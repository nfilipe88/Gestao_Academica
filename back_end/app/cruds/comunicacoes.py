"""
Acesso a dados e regras de negócio de Comunicados/Convocatórias.

O envio efetivo dos e-mails fica na camada de API, via
app.core.fila_notificacoes (fila com retries) — este módulo devolve o
Comunicado criado e a lista de destinatários para quem chamar
despachar o envio.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.models import Usuario
from app.database.models_academico import Turma
from app.database.models_pessoas import Aluno, AlunoResponsavel, Professor, ResponsavelFinanceiroLegal
from app.database.models_matricula import Matricula
from app.database.models_comunicacoes import AnexoComunicacao, Comunicado
from app.database.models_diario import ProfessorTurmaDisciplina
from app.schemas.comunicacoes import ComunicadoCreate
from app.cruds import notificacoes as crud_notificacoes
from app.core import storage
from app.core.paginacao import paginar_linhas

TIPOS_VALIDOS = {"COMUNICADO", "CONVOCATORIA"}
DESTINATARIOS_VALIDOS = {"TURMA", "ALUNO", "ESCOLA"}

# Anexo de um Comunicado (ex.: circular em PDF) — mesmo limite dos
# outros uploads da plataforma (ver app/cruds/configuracoes.py, para o
# logótipo), generoso o suficiente para um documento de algumas
# páginas sem abrir a porta a ficheiros enormes.
_TAMANHO_MAXIMO_ANEXO = 5 * 1024 * 1024  # 5 MB


async def _validar_autoria_professor(
    db: AsyncSession, utilizador: dict, destinatario_tipo: str,
    turma_id: uuid.UUID | None, aluno_id: uuid.UUID | None
) -> None:
    """
    Um Professor só pode comunicar com turmas/alunos das turmas onde
    está efetivamente alocado (Professor_Turma_Disciplina — Nível 1).
    Gestor/Secretaria não passam por aqui (já filtrados antes de chamar isto).
    """
    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"],
            Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=403, detail="Utilizador não corresponde a nenhum professor cadastrado.")

    if destinatario_tipo == "TURMA":
        alocado = (await db.execute(
            select(ProfessorTurmaDisciplina).where(
                ProfessorTurmaDisciplina.professor_id == professor.id,
                ProfessorTurmaDisciplina.turma_id == turma_id
            )
        )).scalars().first()
        if not alocado:
            raise HTTPException(status_code=403, detail="Só pode comunicar com turmas onde lecciona.")

    elif destinatario_tipo == "ALUNO":
        turma_do_aluno = (await db.execute(
            select(Matricula.turma_id).where(
                Matricula.aluno_id == aluno_id,
                Matricula.status_matricula == "ATIVO",
                Matricula.tenant_id == utilizador["tenant_id"]
            )
        )).scalars().all()
        if not turma_do_aluno:
            raise HTTPException(status_code=403, detail="Aluno sem matrícula ativa nesta instituição.")

        alocado = (await db.execute(
            select(ProfessorTurmaDisciplina).where(
                ProfessorTurmaDisciplina.professor_id == professor.id,
                ProfessorTurmaDisciplina.turma_id.in_(turma_do_aluno)
            )
        )).scalars().first()
        if not alocado:
            raise HTTPException(status_code=403, detail="Só pode comunicar com alunos das turmas onde lecciona.")


async def _resolver_emails_destinatarios(
    db: AsyncSession, tenant_id, destinatario_tipo: str,
    turma_id: uuid.UUID | None, aluno_id: uuid.UUID | None
) -> list[str]:
    """
    Traduz "para quem" (Turma/Aluno/Escola) numa lista de e-mails reais.
    Só responsáveis com e-mail preenchido recebem (é opcional no cadastro).
    """
    emails: set[str] = set()

    if destinatario_tipo == "ALUNO":
        resultado = await db.execute(
            select(ResponsavelFinanceiroLegal.email)
            .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
            .where(
                AlunoResponsavel.aluno_id == aluno_id,
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.email.isnot(None)
            )
        )
        emails.update(email for (email,) in resultado.all())

    elif destinatario_tipo == "TURMA":
        # Só os responsáveis de alunos com matrícula ATIVA na turma.
        resultado = await db.execute(
            select(ResponsavelFinanceiroLegal.email)
            .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
            .join(Matricula, Matricula.aluno_id == AlunoResponsavel.aluno_id)
            .where(
                Matricula.turma_id == turma_id,
                Matricula.status_matricula == "ATIVO",
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.email.isnot(None)
            )
        )
        emails.update(email for (email,) in resultado.all())

    elif destinatario_tipo == "ESCOLA":
        responsaveis = await db.execute(
            select(ResponsavelFinanceiroLegal.email).where(
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.email.isnot(None)
            )
        )
        emails.update(email for (email,) in responsaveis.all())

        professores = await db.execute(
            select(Usuario.email)
            .join(Professor, Professor.usuario_id == Usuario.id)
            .where(Professor.tenant_id == tenant_id)
        )
        emails.update(email for (email,) in professores.all())

    return list(emails)


async def _resolver_usuarios_destinatarios(
    db: AsyncSession, tenant_id, destinatario_tipo: str,
    turma_id: uuid.UUID | None, aluno_id: uuid.UUID | None
) -> list[uuid.UUID]:
    """
    Espelha _resolver_emails_destinatarios, mas devolve usuario_id em vez
    de e-mails — usado para gerar notificações in-app. Ao contrário do
    e-mail (só chega aos responsáveis), aqui também inclui o login do
    próprio aluno quando ele tem acesso ao Portal.
    """
    usuario_ids: set[uuid.UUID] = set()

    if destinatario_tipo == "ALUNO":
        aluno_usuario_id = (await db.execute(
            select(Aluno.usuario_id).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id, Aluno.usuario_id.isnot(None))
        )).scalars().first()
        if aluno_usuario_id:
            usuario_ids.add(aluno_usuario_id)

        resultado = await db.execute(
            select(ResponsavelFinanceiroLegal.usuario_id)
            .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
            .where(
                AlunoResponsavel.aluno_id == aluno_id,
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.usuario_id.isnot(None)
            )
        )
        usuario_ids.update(usuario_id for (usuario_id,) in resultado.all())

    elif destinatario_tipo == "TURMA":
        resultado_alunos = await db.execute(
            select(Aluno.usuario_id)
            .join(Matricula, Matricula.aluno_id == Aluno.id)
            .where(
                Matricula.turma_id == turma_id,
                Matricula.status_matricula == "ATIVO",
                Aluno.tenant_id == tenant_id,
                Aluno.usuario_id.isnot(None)
            )
        )
        usuario_ids.update(usuario_id for (usuario_id,) in resultado_alunos.all())

        resultado_resp = await db.execute(
            select(ResponsavelFinanceiroLegal.usuario_id)
            .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
            .join(Matricula, Matricula.aluno_id == AlunoResponsavel.aluno_id)
            .where(
                Matricula.turma_id == turma_id,
                Matricula.status_matricula == "ATIVO",
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.usuario_id.isnot(None)
            )
        )
        usuario_ids.update(usuario_id for (usuario_id,) in resultado_resp.all())

    elif destinatario_tipo == "ESCOLA":
        alunos = await db.execute(
            select(Aluno.usuario_id).where(Aluno.tenant_id == tenant_id, Aluno.usuario_id.isnot(None))
        )
        usuario_ids.update(usuario_id for (usuario_id,) in alunos.all())

        responsaveis = await db.execute(
            select(ResponsavelFinanceiroLegal.usuario_id).where(
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.usuario_id.isnot(None)
            )
        )
        usuario_ids.update(usuario_id for (usuario_id,) in responsaveis.all())

        professores = await db.execute(
            select(Professor.usuario_id).where(Professor.tenant_id == tenant_id)
        )
        usuario_ids.update(usuario_id for (usuario_id,) in professores.all())

    return list(usuario_ids)


async def criar_comunicado(db: AsyncSession, utilizador: dict, dados: ComunicadoCreate) -> tuple[Comunicado, list[str]]:
    """Cria um Comunicado/Convocatória e devolve também a lista de e-mails a notificar."""
    if dados.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use um de: {', '.join(sorted(TIPOS_VALIDOS))}.")
    if dados.destinatario_tipo not in DESTINATARIOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Destinatário inválido. Use um de: {', '.join(sorted(DESTINATARIOS_VALIDOS))}.")

    # RBAC adicional: Professor não pode fazer um comunicado institucional
    # para a escola inteira (isso fica para Gestor/Secretaria).
    if utilizador["perfil_acesso"] == "PROFESSOR" and dados.destinatario_tipo == "ESCOLA":
        raise HTTPException(status_code=403, detail="Professores não podem enviar comunicados para toda a escola.")

    tenant_id = utilizador["tenant_id"]

    if dados.destinatario_tipo == "TURMA":
        if not dados.destinatario_turma_id:
            raise HTTPException(status_code=400, detail="Selecione a turma destinatária.")
        turma = (await db.execute(
            select(Turma).where(Turma.id == dados.destinatario_turma_id, Turma.tenant_id == tenant_id)
        )).scalars().first()
        if not turma:
            raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    if dados.destinatario_tipo == "ALUNO":
        if not dados.destinatario_aluno_id:
            raise HTTPException(status_code=400, detail="Selecione o aluno destinatário.")
        aluno = (await db.execute(
            select(Aluno).where(Aluno.id == dados.destinatario_aluno_id, Aluno.tenant_id == tenant_id)
        )).scalars().first()
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    if utilizador["perfil_acesso"] == "PROFESSOR":
        await _validar_autoria_professor(
            db, utilizador, dados.destinatario_tipo, dados.destinatario_turma_id, dados.destinatario_aluno_id
        )

    emails = await _resolver_emails_destinatarios(
        db, tenant_id, dados.destinatario_tipo, dados.destinatario_turma_id, dados.destinatario_aluno_id
    )

    novo_comunicado = Comunicado(
        tenant_id=tenant_id,
        autor_id=utilizador["usuario_id"],
        tipo=dados.tipo,
        titulo=dados.titulo,
        corpo=dados.corpo,
        destinatario_tipo=dados.destinatario_tipo,
        destinatario_turma_id=dados.destinatario_turma_id,
        destinatario_aluno_id=dados.destinatario_aluno_id,
        total_destinatarios=len(emails)
    )
    db.add(novo_comunicado)
    await db.commit()
    await db.refresh(novo_comunicado)

    usuario_ids = await _resolver_usuarios_destinatarios(
        db, tenant_id, dados.destinatario_tipo, dados.destinatario_turma_id, dados.destinatario_aluno_id
    )
    await crud_notificacoes.criar_notificacoes_em_lote(
        db, tenant_id, usuario_ids,
        tipo="COMUNICADO",
        titulo=f"Novo {dados.tipo.lower()}: {dados.titulo}",
        mensagem=dados.corpo[:280],
        link="/comunicacoes"
    )

    return novo_comunicado, emails


async def listar_comunicados(db: AsyncSession, tenant_id, page: int, page_size: int) -> dict:
    """Lista o histórico de comunicados/convocatórias enviados pela escola, paginado."""
    query = (
        select(Comunicado, Usuario.nome_completo)
        .outerjoin(Usuario, Usuario.id == Comunicado.autor_id)
        .where(Comunicado.tenant_id == tenant_id)
        .order_by(Comunicado.data_envio.desc())
    )
    pagina = await paginar_linhas(db, query, page, page_size)
    linhas = pagina["items"]

    ids_pagina = [comunicado.id for comunicado, _ in linhas]
    ids_com_anexo: set[uuid.UUID] = set()
    if ids_pagina:
        resultado = await db.execute(
            select(AnexoComunicacao.comunicado_id).where(
                AnexoComunicacao.tenant_id == tenant_id, AnexoComunicacao.comunicado_id.in_(ids_pagina)
            )
        )
        ids_com_anexo = {comunicado_id for (comunicado_id,) in resultado.all()}

    pagina["items"] = [
        {
            "id": comunicado.id,
            "autor_nome": autor_nome or "—",
            "tipo": comunicado.tipo,
            "titulo": comunicado.titulo,
            "corpo": comunicado.corpo,
            "destinatario_tipo": comunicado.destinatario_tipo,
            "destinatario_turma_id": comunicado.destinatario_turma_id,
            "destinatario_aluno_id": comunicado.destinatario_aluno_id,
            "total_destinatarios": comunicado.total_destinatarios,
            "data_envio": comunicado.data_envio,
            "tem_anexo": comunicado.id in ids_com_anexo,
        }
        for comunicado, autor_nome in linhas
    ]
    return pagina


# ==========================================
# ANEXOS
# ==========================================
async def _obter_comunicado(db: AsyncSession, tenant_id, comunicado_id: uuid.UUID) -> Comunicado:
    comunicado = (await db.execute(
        select(Comunicado).where(Comunicado.id == comunicado_id, Comunicado.tenant_id == tenant_id)
    )).scalars().first()
    if not comunicado:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado na sua instituição.")
    return comunicado


async def adicionar_anexo(db: AsyncSession, tenant_id, comunicado_id: uuid.UUID, nome_original: str, content_type: str, conteudo: bytes) -> AnexoComunicacao:
    """Um Comunicado só pode ter um anexo — um novo upload substitui o
    anterior (mesmo padrão do logótipo da escola, ver
    cruds/configuracoes.py::atualizar_logotipo)."""
    if len(conteudo) > _TAMANHO_MAXIMO_ANEXO:
        raise HTTPException(status_code=400, detail="O anexo não pode passar de 5 MB.")

    await _obter_comunicado(db, tenant_id, comunicado_id)

    anexo_existente = (await db.execute(
        select(AnexoComunicacao).where(AnexoComunicacao.comunicado_id == comunicado_id, AnexoComunicacao.tenant_id == tenant_id)
    )).scalars().first()

    chave = storage.gerar_chave(tenant_id, "comunicado", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    if anexo_existente:
        chave_antiga = anexo_existente.chave_storage
        anexo_existente.chave_storage = chave
        anexo_existente.nome_original = nome_original
        anexo_existente.content_type = content_type
        anexo_existente.tamanho_bytes = len(conteudo)
        anexo = anexo_existente
        await db.commit()
        await db.refresh(anexo)
        await storage.apagar_ficheiro(chave_antiga)
    else:
        anexo = AnexoComunicacao(
            tenant_id=tenant_id, comunicado_id=comunicado_id, chave_storage=chave,
            nome_original=nome_original, content_type=content_type, tamanho_bytes=len(conteudo),
        )
        db.add(anexo)
        await db.commit()
        await db.refresh(anexo)

    return anexo


async def obter_anexo_metadados(db: AsyncSession, tenant_id, comunicado_id: uuid.UUID) -> AnexoComunicacao | None:
    return (await db.execute(
        select(AnexoComunicacao).where(AnexoComunicacao.comunicado_id == comunicado_id, AnexoComunicacao.tenant_id == tenant_id)
    )).scalars().first()


async def obter_anexo_conteudo(db: AsyncSession, tenant_id, comunicado_id: uuid.UUID) -> tuple[bytes, str, str]:
    anexo = await obter_anexo_metadados(db, tenant_id, comunicado_id)
    if not anexo:
        raise HTTPException(status_code=404, detail="Este comunicado não tem nenhum anexo.")
    conteudo = await storage.obter_ficheiro(anexo.chave_storage)
    if not conteudo:
        raise HTTPException(status_code=404, detail="Anexo registado mas o ficheiro não foi encontrado no armazenamento.")
    return conteudo, anexo.content_type, anexo.nome_original
