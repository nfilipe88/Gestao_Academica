"""Acesso a dados de Alunos, Responsáveis e o vínculo entre eles.

O envio de e-mail de notificação (RN de vínculo) fica na camada de API,
não aqui — depende de app.core.fila_notificacoes, que é uma
preocupação de transporte, não de acesso a dados.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, update
import uuid

from datetime import date

from app.database.models import Tenant, Usuario
from app.database.models_academico import Turma
from app.database.models_documentos import TemplateDocumentoPersonalizado
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, AlunoDocumento, AlunoResponsavel, FotoPerfilAluno, ResponsavelFinanceiroLegal
from app.core import documentos_pdf, storage
from app.core.security import gerar_hash_senha
from app.core.paginacao import paginar
from app.schemas.alunos import AlunoCreate, CriarAcessoRequest, ResponsavelCreate, VincularResponsavel

# Documentos do aluno (sobretudo Histórico Escolar anexado
# automaticamente na Transferência/Reingresso cross-escola — ver
# cruds/transferencias.py::aprovar_e_migrar) — mesmos limites de
# MatriculaDocumento (cruds/matriculas.py).
_TIPOS_FICHEIRO_ACEITES = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}
_TAMANHO_MAXIMO_DOCUMENTO = 8 * 1024 * 1024  # 8 MB
_MAX_DOCUMENTOS_POR_ALUNO = 10

# Foto de perfil (a que vale para o cartão de acesso — ver
# FotoPerfilAluno). Só imagens (sem PDF/GIF — não faz sentido para uma
# foto tipo cartão) e um limite mais apertado do que os documentos de
# apoio, que costumam ser digitalizações.
_TIPOS_FOTO_ACEITES = {"image/png", "image/jpeg", "image/webp"}
_TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024  # 5 MB


# ==========================================
# RESOLUÇÃO DE ACESSO (que aluno_id um login ALUNO/RESPONSAVEL pode ver)
#
# Extraído aqui (em vez de duplicado) porque tanto o Portal como os
# Pedidos de Documentos precisam da mesma pergunta: "a que aluno_id(s)
# este login tem direito?". Aluno é o dono natural desta regra.
# ==========================================
async def resolver_meus_alunos(db: AsyncSession, tenant_id, utilizador: dict) -> list[uuid.UUID]:
    perfil = utilizador.get("perfil_acesso")
    if perfil == "ALUNO":
        aluno_id = (await db.execute(
            select(Aluno.id).where(Aluno.usuario_id == utilizador["usuario_id"], Aluno.tenant_id == tenant_id)
        )).scalar_one_or_none()
        return [aluno_id] if aluno_id else []
    if perfil == "RESPONSAVEL":
        responsavel_id = (await db.execute(
            select(ResponsavelFinanceiroLegal.id).where(
                ResponsavelFinanceiroLegal.usuario_id == utilizador["usuario_id"],
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if not responsavel_id:
            return []
        ids = (await db.execute(
            select(AlunoResponsavel.aluno_id).where(AlunoResponsavel.responsavel_id == responsavel_id)
        )).scalars().all()
        return list(ids)
    return []


async def garantir_aluno_permitido(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> Aluno:
    permitidos = await resolver_meus_alunos(db, tenant_id, utilizador)
    if aluno_id not in permitidos:
        raise HTTPException(status_code=403, detail="Sem acesso a este aluno.")
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
    return aluno


async def criar_aluno(db: AsyncSession, tenant_id, dados: AlunoCreate) -> Aluno:
    ja_existe = await db.execute(
        select(Aluno).where(Aluno.tenant_id == tenant_id, Aluno.matricula_interna == dados.matricula_interna)
    )
    if ja_existe.scalars().first():
        raise HTTPException(status_code=400, detail="Já existe um aluno com esta matrícula interna.")

    novo_aluno = Aluno(
        tenant_id=tenant_id,
        matricula_interna=dados.matricula_interna,
        nome_completo=dados.nome_completo,
        data_nascimento=dados.data_nascimento,
        numero_documento=dados.numero_documento
    )
    db.add(novo_aluno)
    await db.commit()
    await db.refresh(novo_aluno)
    return novo_aluno


async def listar_alunos(
    db: AsyncSession, tenant_id, page: int, page_size: int,
    busca: str | None = None, data_nascimento_inicio=None, data_nascimento_fim=None
) -> dict:
    query = select(Aluno).where(Aluno.tenant_id == tenant_id)
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.where(or_(
            Aluno.nome_completo.ilike(termo),
            Aluno.matricula_interna.ilike(termo),
            Aluno.numero_documento.ilike(termo)
        ))
    if data_nascimento_inicio:
        query = query.where(Aluno.data_nascimento >= data_nascimento_inicio)
    if data_nascimento_fim:
        query = query.where(Aluno.data_nascimento <= data_nascimento_fim)
    query = query.order_by(Aluno.nome_completo)
    return await paginar(db, query, page, page_size)


async def criar_responsavel(db: AsyncSession, tenant_id, dados: ResponsavelCreate) -> ResponsavelFinanceiroLegal:
    novo_responsavel = ResponsavelFinanceiroLegal(
        tenant_id=tenant_id,
        nome_completo=dados.nome_completo,
        telefone_contato=dados.telefone_contato,
        numero_documento=dados.numero_documento,
        email=dados.email
    )
    db.add(novo_responsavel)
    await db.commit()
    await db.refresh(novo_responsavel)
    return novo_responsavel


async def listar_responsaveis(db: AsyncSession, tenant_id, page: int, page_size: int) -> dict:
    query = select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.tenant_id == tenant_id).order_by(ResponsavelFinanceiroLegal.nome_completo)
    return await paginar(db, query, page, page_size)


async def vincular_responsavel(
    db: AsyncSession, tenant_id, aluno_id: uuid.UUID, dados: VincularResponsavel
) -> tuple[AlunoResponsavel, Aluno, ResponsavelFinanceiroLegal]:
    """Vincula um responsável já existente a um aluno (RN: um aluno pode ter vários responsáveis).

    Devolve também o Aluno e o Responsável para quem chamar poder
    compor o e-mail de notificação sem uma segunda ida à base de dados.
    """
    aluno_db = await db.execute(select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id))
    aluno = aluno_db.scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    responsavel_db = await db.execute(
        select(ResponsavelFinanceiroLegal).where(
            ResponsavelFinanceiroLegal.id == dados.responsavel_id,
            ResponsavelFinanceiroLegal.tenant_id == tenant_id
        )
    )
    responsavel = responsavel_db.scalars().first()
    if not responsavel:
        raise HTTPException(status_code=404, detail="Responsável não encontrado na sua instituição.")

    ja_vinculado = await db.execute(
        select(AlunoResponsavel).where(
            AlunoResponsavel.aluno_id == aluno_id,
            AlunoResponsavel.responsavel_id == dados.responsavel_id
        )
    )
    if ja_vinculado.scalars().first():
        raise HTTPException(status_code=400, detail="Este responsável já está vinculado a este aluno.")

    vinculo = AlunoResponsavel(
        tenant_id=tenant_id,
        aluno_id=aluno_id,
        responsavel_id=dados.responsavel_id,
        tipo_parentesco=dados.tipo_parentesco,
        responsavel_financeiro=dados.responsavel_financeiro
    )
    db.add(vinculo)
    await db.commit()
    return vinculo, aluno, responsavel


async def listar_responsaveis_do_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> list[AlunoResponsavel]:
    resultado = await db.execute(
        select(AlunoResponsavel).where(AlunoResponsavel.aluno_id == aluno_id, AlunoResponsavel.tenant_id == tenant_id)
    )
    return resultado.scalars().all()


# ==========================================
# ACESSO AO PORTAL (login próprio para Aluno/Responsável)
# ==========================================
async def _criar_acesso(db: AsyncSession, tenant_id, dados: CriarAcessoRequest, perfil_acesso: str, nome_completo: str) -> Usuario:
    """Cria o Usuario (perfil_acesso=ALUNO/RESPONSAVEL) que o registo de Aluno/Responsável vai passar a referenciar."""
    email_existente = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if email_existente.scalars().first():
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    novo_usuario = Usuario(
        tenant_id=tenant_id,
        nome_completo=nome_completo,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.palavra_passe),
        perfil_acesso=perfil_acesso,
    )
    db.add(novo_usuario)
    await db.flush()
    return novo_usuario


async def criar_acesso_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, dados: CriarAcessoRequest) -> Usuario:
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
    if aluno.usuario_id:
        raise HTTPException(status_code=400, detail="Este aluno já tem acesso ao Portal.")

    try:
        novo_usuario = await _criar_acesso(db, tenant_id, dados, "ALUNO", aluno.nome_completo)
        aluno.usuario_id = novo_usuario.id
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    await db.refresh(novo_usuario)
    return novo_usuario


async def criar_acesso_responsavel(db: AsyncSession, tenant_id, responsavel_id: uuid.UUID, dados: CriarAcessoRequest) -> Usuario:
    responsavel = (await db.execute(
        select(ResponsavelFinanceiroLegal).where(
            ResponsavelFinanceiroLegal.id == responsavel_id, ResponsavelFinanceiroLegal.tenant_id == tenant_id
        )
    )).scalars().first()
    if not responsavel:
        raise HTTPException(status_code=404, detail="Responsável não encontrado na sua instituição.")
    if responsavel.usuario_id:
        raise HTTPException(status_code=400, detail="Este responsável já tem acesso ao Portal.")

    try:
        novo_usuario = await _criar_acesso(db, tenant_id, dados, "RESPONSAVEL", responsavel.nome_completo)
        responsavel.usuario_id = novo_usuario.id
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    await db.refresh(novo_usuario)
    return novo_usuario


# ==========================================
# DOCUMENTOS DO ALUNO (sobretudo Histórico Escolar de Transferência/Reingresso)
# ==========================================
async def _obter_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> Aluno:
    aluno = (await db.execute(select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id))).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
    return aluno


async def _listar_documentos_aluno(db: AsyncSession, tenant_id, aluno_id) -> list[AlunoDocumento]:
    return (await db.execute(
        select(AlunoDocumento).where(AlunoDocumento.tenant_id == tenant_id, AlunoDocumento.aluno_id == aluno_id)
        .order_by(AlunoDocumento.data_criacao)
    )).scalars().all()


def _serializar_documento_aluno(d: AlunoDocumento) -> dict:
    return {"id": d.id, "descricao": d.descricao, "nome_original": d.nome_original}


async def listar_documentos_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> list[dict]:
    await _obter_aluno(db, tenant_id, aluno_id)
    return [_serializar_documento_aluno(d) for d in await _listar_documentos_aluno(db, tenant_id, aluno_id)]


async def adicionar_documento_aluno(
    db: AsyncSession, tenant_id, aluno_id: uuid.UUID, descricao: str | None,
    nome_original: str, content_type: str, conteudo: bytes
) -> list[dict]:
    if content_type not in _TIPOS_FICHEIRO_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato não aceite ({content_type}). Use PNG, JPEG, GIF, WebP ou PDF.")
    if len(conteudo) > _TAMANHO_MAXIMO_DOCUMENTO:
        raise HTTPException(status_code=400, detail="Cada documento não pode passar de 8 MB.")

    await _obter_aluno(db, tenant_id, aluno_id)
    total_atual = len(await _listar_documentos_aluno(db, tenant_id, aluno_id))
    if total_atual >= _MAX_DOCUMENTOS_POR_ALUNO:
        raise HTTPException(status_code=400, detail=f"Já tem o máximo de {_MAX_DOCUMENTOS_POR_ALUNO} documentos anexados a este aluno.")

    chave = storage.gerar_chave(tenant_id, "aluno", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    db.add(AlunoDocumento(
        tenant_id=tenant_id, aluno_id=aluno_id, descricao=(descricao or "").strip() or None,
        nome_original=nome_original, chave_storage=chave
    ))
    await db.commit()
    return [_serializar_documento_aluno(d) for d in await _listar_documentos_aluno(db, tenant_id, aluno_id)]


async def remover_documento_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, documento_id: uuid.UUID) -> list[dict]:
    await _obter_aluno(db, tenant_id, aluno_id)
    documento = (await db.execute(
        select(AlunoDocumento).where(
            AlunoDocumento.id == documento_id, AlunoDocumento.aluno_id == aluno_id, AlunoDocumento.tenant_id == tenant_id
        )
    )).scalars().first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    chave = documento.chave_storage
    await db.delete(documento)
    await db.commit()
    await storage.apagar_ficheiro(chave)
    return [_serializar_documento_aluno(d) for d in await _listar_documentos_aluno(db, tenant_id, aluno_id)]


async def obter_documento_aluno_url(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, documento_id: uuid.UUID) -> str:
    documento = (await db.execute(
        select(AlunoDocumento).where(
            AlunoDocumento.id == documento_id, AlunoDocumento.aluno_id == aluno_id, AlunoDocumento.tenant_id == tenant_id
        )
    )).scalars().first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    url = await storage.obter_data_uri(documento.chave_storage)
    if not url:
        raise HTTPException(status_code=404, detail="Ficheiro do documento já não está disponível.")
    return url


async def anexar_documento_gerado(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, descricao: str, nome_ficheiro: str, conteudo_pdf: bytes) -> None:
    """Anexa um PDF gerado internamente pela plataforma (não um upload
    do utilizador) — usada por cruds/transferencias.py::aprovar_e_migrar
    para o Histórico Escolar automático. Sem validação de tipo/tamanho
    de ficheiro (o PDF já foi gerado por nós) nem do limite de
    _MAX_DOCUMENTOS_POR_ALUNO (o aluno acabou de ser criado, nunca terá
    outros documentos ainda). Não faz commit — quem chama decide
    quando fechar a transação, para ficar na mesma unidade atómica que
    a criação do próprio aluno."""
    chave = storage.gerar_chave(tenant_id, "aluno", nome_ficheiro)
    await storage.guardar_ficheiro(chave, conteudo_pdf, "application/pdf")
    db.add(AlunoDocumento(tenant_id=tenant_id, aluno_id=aluno_id, descricao=descricao, nome_original=nome_ficheiro, chave_storage=chave))


# ==========================================
# FOTO DE PERFIL (a que vale para o cartão de acesso — ver
# FotoPerfilAluno, models_pessoas.py). Deve ser renovada todos os
# anos, mas isso não é um bloqueio: enviar não apaga nada, arquiva.
# ==========================================
def _serializar_foto_perfil(f: FotoPerfilAluno) -> dict:
    return {
        "id": f.id, "ano_letivo": f.ano_letivo, "ativa": f.ativa,
        "nome_original": f.nome_original, "data_envio": f.data_envio,
    }


async def _listar_fotos_perfil(db: AsyncSession, tenant_id, aluno_id) -> list[FotoPerfilAluno]:
    return (await db.execute(
        select(FotoPerfilAluno).where(FotoPerfilAluno.tenant_id == tenant_id, FotoPerfilAluno.aluno_id == aluno_id)
        .order_by(FotoPerfilAluno.data_envio.desc())
    )).scalars().all()


async def listar_fotos_perfil(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> list[dict]:
    await _obter_aluno(db, tenant_id, aluno_id)
    return [_serializar_foto_perfil(f) for f in await _listar_fotos_perfil(db, tenant_id, aluno_id)]


async def enviar_foto_perfil(
    db: AsyncSession, tenant_id, aluno_id: uuid.UUID, usuario_id,
    nome_original: str, content_type: str, conteudo: bytes
) -> list[dict]:
    if content_type not in _TIPOS_FOTO_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato não aceite ({content_type}). Use PNG, JPEG ou WebP.")
    if len(conteudo) > _TAMANHO_MAXIMO_FOTO:
        raise HTTPException(status_code=400, detail="A fotografia não pode passar de 5 MB.")

    await _obter_aluno(db, tenant_id, aluno_id)

    # Arquiva a ativa atual (se houver) — nunca é apagada, só deixa de
    # valer para o cartão. É assim que a evolução do aluno ao longo
    # dos anos fica visível no histórico.
    await db.execute(
        update(FotoPerfilAluno)
        .where(FotoPerfilAluno.tenant_id == tenant_id, FotoPerfilAluno.aluno_id == aluno_id, FotoPerfilAluno.ativa.is_(True))
        .values(ativa=False)
    )

    chave = storage.gerar_chave(tenant_id, "aluno", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    db.add(FotoPerfilAluno(
        tenant_id=tenant_id, aluno_id=aluno_id, ano_letivo=date.today().year,
        nome_original=nome_original, chave_storage=chave, ativa=True,
        enviada_por_usuario_id=usuario_id,
    ))
    await db.commit()
    return [_serializar_foto_perfil(f) for f in await _listar_fotos_perfil(db, tenant_id, aluno_id)]


async def obter_foto_perfil_url(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, foto_id: uuid.UUID) -> str:
    foto = (await db.execute(
        select(FotoPerfilAluno).where(
            FotoPerfilAluno.id == foto_id, FotoPerfilAluno.aluno_id == aluno_id, FotoPerfilAluno.tenant_id == tenant_id
        )
    )).scalars().first()
    if not foto:
        raise HTTPException(status_code=404, detail="Fotografia não encontrada.")
    url = await storage.obter_data_uri(foto.chave_storage)
    if not url:
        raise HTTPException(status_code=404, detail="Ficheiro da fotografia já não está disponível.")
    return url


async def gerar_cartao_acesso(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> bytes:
    """PDF de formato cartão (CR80, ver documentos_pdf.py) com a foto de
    perfil ATIVA do aluno — não é um "documento" pedido/pago pela
    família (ver Solicitações de Documentos), é emitido diretamente
    pela escola sob pedido. Não bloqueia se faltar foto ou matrícula
    (mostra espaço reservado/"—") — a Secretaria pode querer emitir o
    cartão antes de qualquer um dos dois estar pronto.

    Personalizável por escola (ver cruds/documentos.py::
    TIPOS_DOCUMENTO_PERSONALIZAVEL) — se o tenant tiver um layout
    próprio ativo para "CARTAO_ACESSO", é ele que desenha o cartão, não
    o nativo. A consulta ao template é feita aqui diretamente (não via
    cruds/documentos.py::obter_template_personalizado_ativo) para não
    criar um import circular — documentos.py já importa este módulo."""
    aluno = await _obter_aluno(db, tenant_id, aluno_id)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()

    matricula_turma = (await db.execute(
        select(Matricula.ano_letivo, Turma.nome_codigo)
        .join(Turma, Turma.id == Matricula.turma_id)
        .where(Matricula.tenant_id == tenant_id, Matricula.aluno_id == aluno_id)
        .order_by(Matricula.status_matricula != "ATIVO", Matricula.ano_letivo.desc())
    )).first()

    foto_ativa = (await db.execute(
        select(FotoPerfilAluno).where(
            FotoPerfilAluno.tenant_id == tenant_id, FotoPerfilAluno.aluno_id == aluno_id, FotoPerfilAluno.ativa.is_(True)
        )
    )).scalars().first()
    foto_data_uri = await storage.obter_data_uri(foto_ativa.chave_storage) if foto_ativa else None

    template = (await db.execute(
        select(TemplateDocumentoPersonalizado).where(
            TemplateDocumentoPersonalizado.tenant_id == tenant_id,
            TemplateDocumentoPersonalizado.tipo_documento == "CARTAO_ACESSO",
            TemplateDocumentoPersonalizado.ativo == True,  # noqa: E712
        )
    )).scalars().first()

    escola = {
        "nome": tenant.nome_fantasia if tenant else "",
        "logo_data_uri": await storage.obter_logo_data_uri(tenant) if tenant else None,
    }
    dados = {
        "aluno_nome": aluno.nome_completo,
        "matricula_interna": aluno.matricula_interna,
        "turma_nome": matricula_turma.nome_codigo if matricula_turma else None,
        "ano_letivo": matricula_turma.ano_letivo if matricula_turma else None,
        "foto_data_uri": foto_data_uri,
    }
    return documentos_pdf.gerar_pdf_cartao_acesso(
        escola, dados, corpo_html_personalizado=template.corpo_html if template else None
    )
