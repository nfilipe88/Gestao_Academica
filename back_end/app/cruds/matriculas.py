"""Acesso a dados e regras de negócio (RN01-RN05) de Matrículas."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
import uuid

from app.database.models_academico import Turma
from app.database.models_pessoas import Aluno
from app.database.models_matricula import Matricula, MatriculaDocumento, PedidoRematricula
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade
from app.schemas.matriculas import MatriculaCreate, MatriculaStatusUpdate
from app.core import storage
from app.cruds.admin import esta_bloqueado_parcialmente

ESTADOS_VALIDOS = {"ATIVO", "TRANSFERIDO", "TRANCADO", "EVADIDO", "CICLO_CONCLUIDO", "EM_TRANSFERENCIA"}

# EM_TRANSFERENCIA: colocado automaticamente por
# transferencias.py::criar_solicitacao quando uma transferência "a
# quente" (matrícula ATIVO) é pedida — o aluno fica "em suspenso" na
# escola de origem enquanto a escola de destino decide (por isso some
# das listagens que filtram por ATIVO, ex. turmas/rematrícula). Volta
# a ATIVO se a escola de destino rejeitar, ou passa a TRANSFERIDO se
# aprovar. Tal como TRANSFERIDO, também pode ser corrigido à mão por
# aqui em caso de necessidade.

# "Fim de Ciclo" (RN06) — o aluno deixa de ter matrícula ativa nesta
# escola porque foi para uma escola fora da plataforma, ou porque
# concluiu a escolaridade. Distinto de TRANSFERIDO, que é só para o
# fluxo formal entre escolas da própria plataforma (ver
# app/cruds/transferencias.py) — aqui a escola de destino, a existir,
# não está nesta base de dados, por isso não há automação nenhuma a
# fazer, só o registo do motivo.
MOTIVOS_FIM_CICLO_VALIDOS = {"TRANSFERENCIA_EXTERNA", "CONCLUSAO_ESCOLARIDADE", "OUTRO"}

# Documentos de apoio a uma matrícula (sobretudo Reingresso — ver
# MatriculaDocumento).
_TIPOS_FICHEIRO_ACEITES = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}
_TAMANHO_MAXIMO_DOCUMENTO = 8 * 1024 * 1024  # 8 MB
_MAX_DOCUMENTOS_POR_MATRICULA = 10


# ==========================================
# RN05 do Financeiro (Nível 2) — Bloqueios Legais
# ==========================================
# "Por regras governamentais [...] um aluno inadimplente não pode ser
# impedido de frequentar aulas [...] durante o ano letivo em curso [...]
# O bloqueio real só ocorre na tentativa de Renovação de Matrícula para
# o ano seguinte." — por isso o bloqueio vive aqui (criar_matricula),
# não em lado nenhum do módulo académico do dia a dia (Diário de
# Classe, etc. continuam sempre acessíveis).
async def tem_mensalidade_em_atraso_de_ano_anterior(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, ano_letivo_novo: int) -> bool:
    """
    Só bloqueia se isto for de facto uma RENOVAÇÃO: o aluno já teve
    matrícula num ano letivo anterior, e essa matrícula tem um
    Contrato_Financeiro com pelo menos uma Fatura_Mensalidade
    verdadeiramente em atraso (pendente e já passada a data de
    vencimento) — o cálculo de juros/multa em si (RN02) é irrelevante
    aqui, só interessa o facto de estar por pagar.

    Não é privada (sem "_") de propósito: reaproveitada por
    listar_candidatos_rematricula (ecrã de Rematrícula) e por
    cruds/portal.py::pedir_rematricula (rematrícula self-service) para
    mostrarem exatamente o mesmo bloqueio que criar_matricula vai
    aplicar de facto — nunca uma cópia da regra que possa divergir.
    """
    matriculas_anteriores = (await db.execute(
        select(Matricula.id).where(
            Matricula.aluno_id == aluno_id,
            Matricula.tenant_id == tenant_id,
            Matricula.ano_letivo < ano_letivo_novo,
        )
    )).scalars().all()
    if not matriculas_anteriores:
        return False

    tem_atraso = (await db.execute(
        select(func.count()).select_from(FaturaMensalidade)
        .join(ContratoFinanceiro, ContratoFinanceiro.id == FaturaMensalidade.contrato_id)
        .where(
            ContratoFinanceiro.matricula_id.in_(matriculas_anteriores),
            FaturaMensalidade.status_pagamento == "PENDENTE",
            FaturaMensalidade.data_vencimento < date.today(),
        )
    )).scalar_one()
    return tem_atraso > 0


async def criar_matricula(db: AsyncSession, tenant_id, dados: MatriculaCreate) -> Matricula:
    """Efetua a matrícula de um aluno numa turma, aplicando as regras de negócio RN01-RN05."""
    # Sanção progressiva do Super Admin (licença vencida há 15+ dias) —
    # ver app/cruds/admin.py::esta_bloqueado_parcialmente. Verificado
    # primeiro, antes de qualquer outra validação: não faz sentido
    # gastar uma consulta a validar aluno/turma só para bloquear no fim.
    if await esta_bloqueado_parcialmente(db, tenant_id):
        raise HTTPException(
            status_code=403,
            detail="A licença desta escola está vencida há mais de 15 dias — novas matrículas ficam bloqueadas até regularizar a situação junto do Super Admin."
        )

    # RN01 + RN05 - Isolamento de tenant e integridade: aluno e turma têm
    # de existir e pertencer à mesma escola do utilizador.
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == dados.aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    turma = (await db.execute(
        select(Turma).where(Turma.id == dados.turma_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    # RN03 - Prevenção de Duplicidade
    duplicado = (await db.execute(
        select(Matricula).where(
            Matricula.aluno_id == dados.aluno_id,
            Matricula.turma_id == dados.turma_id,
            Matricula.ano_letivo == dados.ano_letivo
        )
    )).scalars().first()
    if duplicado:
        raise HTTPException(status_code=400, detail="Este aluno já está matriculado nesta turma neste ano letivo.")

    # RN05 do Financeiro — renovação bloqueada por mensalidade em atraso de ano anterior.
    if await tem_mensalidade_em_atraso_de_ano_anterior(db, tenant_id, dados.aluno_id, dados.ano_letivo):
        raise HTTPException(
            status_code=403,
            detail="Renovação de matrícula bloqueada: existem mensalidades em atraso de um ano letivo anterior. "
                   "Regularize a situação financeira em Financeiro antes de renovar."
        )

    # RN02 - Controlo de Vagas (só conta matrículas ATIVAS)
    total_ativas = (await db.execute(
        select(func.count()).select_from(Matricula).where(
            Matricula.turma_id == dados.turma_id,
            Matricula.status_matricula == "ATIVO"
        )
    )).scalar_one()
    if total_ativas >= turma.vagas_maximas:
        raise HTTPException(status_code=400, detail="Turma lotada — não há vagas disponíveis.")

    # RN04 - Status Inicial "ATIVO"
    nova_matricula = Matricula(
        tenant_id=tenant_id,
        aluno_id=dados.aluno_id,
        turma_id=dados.turma_id,
        ano_letivo=dados.ano_letivo,
        status_matricula="ATIVO"
    )
    db.add(nova_matricula)
    await db.commit()
    await db.refresh(nova_matricula)
    return nova_matricula


async def listar_matriculas_da_turma(db: AsyncSession, tenant_id, turma_id: uuid.UUID, status_matricula: str | None = None) -> list[dict]:
    """Lista os alunos matriculados numa turma. status_matricula="ATIVO" filtra só os ativos."""
    query = (
        select(Matricula, Aluno.nome_completo, Aluno.matricula_interna)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(Matricula.turma_id == turma_id, Matricula.tenant_id == tenant_id)
    )
    if status_matricula:
        query = query.where(Matricula.status_matricula == status_matricula)

    resultado = await db.execute(query)
    return [
        {
            "matricula_id": matricula.id,
            "aluno_id": matricula.aluno_id,
            "nome_aluno": nome_aluno,
            "matricula_interna": matricula_interna,
            "status_matricula": matricula.status_matricula,
            "ano_letivo": matricula.ano_letivo,
            "data_matricula": matricula.data_matricula,
        }
        for matricula, nome_aluno, matricula_interna in resultado.all()
    ]


async def atualizar_status_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, dados: MatriculaStatusUpdate) -> None:
    """Atualiza a situação do aluno (ex: de Ativo para Trancado, Transferido, Evadido ou Ciclo Concluído — Fim de Ciclo)."""
    if dados.status_matricula not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Use um de: {', '.join(sorted(ESTADOS_VALIDOS))}."
        )
    if dados.status_matricula == "CICLO_CONCLUIDO" and dados.motivo not in MOTIVOS_FIM_CICLO_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Indique o motivo do Fim de Ciclo — um de: {', '.join(sorted(MOTIVOS_FIM_CICLO_VALIDOS))}."
        )

    matricula = (await db.execute(
        select(Matricula).where(Matricula.id == matricula_id, Matricula.tenant_id == tenant_id)
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada na sua instituição.")

    matricula.status_matricula = dados.status_matricula
    matricula.motivo = dados.motivo
    await db.commit()


# ==========================================
# DOCUMENTOS DA MATRÍCULA (sobretudo Reingresso)
# ==========================================
async def _obter_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID) -> Matricula:
    matricula = (await db.execute(
        select(Matricula).where(Matricula.id == matricula_id, Matricula.tenant_id == tenant_id)
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada na sua instituição.")
    return matricula


async def _listar_documentos_matricula(db: AsyncSession, tenant_id, matricula_id) -> list[MatriculaDocumento]:
    return (await db.execute(
        select(MatriculaDocumento).where(MatriculaDocumento.tenant_id == tenant_id, MatriculaDocumento.matricula_id == matricula_id)
        .order_by(MatriculaDocumento.data_criacao)
    )).scalars().all()


def _serializar_documento(d: MatriculaDocumento) -> dict:
    return {"id": d.id, "descricao": d.descricao, "nome_original": d.nome_original}


async def listar_documentos_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID) -> list[dict]:
    await _obter_matricula(db, tenant_id, matricula_id)
    return [_serializar_documento(d) for d in await _listar_documentos_matricula(db, tenant_id, matricula_id)]


async def adicionar_documento_matricula(
    db: AsyncSession, tenant_id, matricula_id: uuid.UUID, descricao: str | None,
    nome_original: str, content_type: str, conteudo: bytes
) -> list[dict]:
    if content_type not in _TIPOS_FICHEIRO_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato não aceite ({content_type}). Use PNG, JPEG, GIF, WebP ou PDF.")
    if len(conteudo) > _TAMANHO_MAXIMO_DOCUMENTO:
        raise HTTPException(status_code=400, detail="Cada documento não pode passar de 8 MB.")

    await _obter_matricula(db, tenant_id, matricula_id)
    total_atual = len(await _listar_documentos_matricula(db, tenant_id, matricula_id))
    if total_atual >= _MAX_DOCUMENTOS_POR_MATRICULA:
        raise HTTPException(status_code=400, detail=f"Já tem o máximo de {_MAX_DOCUMENTOS_POR_MATRICULA} documentos anexados a esta matrícula.")

    chave = storage.gerar_chave(tenant_id, "matricula", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    db.add(MatriculaDocumento(
        tenant_id=tenant_id, matricula_id=matricula_id, descricao=(descricao or "").strip() or None,
        nome_original=nome_original, chave_storage=chave
    ))
    await db.commit()
    return [_serializar_documento(d) for d in await _listar_documentos_matricula(db, tenant_id, matricula_id)]


async def remover_documento_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, documento_id: uuid.UUID) -> list[dict]:
    await _obter_matricula(db, tenant_id, matricula_id)
    documento = (await db.execute(
        select(MatriculaDocumento).where(
            MatriculaDocumento.id == documento_id, MatriculaDocumento.matricula_id == matricula_id, MatriculaDocumento.tenant_id == tenant_id
        )
    )).scalars().first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    chave = documento.chave_storage
    await db.delete(documento)
    await db.commit()
    await storage.apagar_ficheiro(chave)
    return [_serializar_documento(d) for d in await _listar_documentos_matricula(db, tenant_id, matricula_id)]


async def obter_documento_matricula_url(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, documento_id: uuid.UUID) -> str:
    documento = (await db.execute(
        select(MatriculaDocumento).where(
            MatriculaDocumento.id == documento_id, MatriculaDocumento.matricula_id == matricula_id, MatriculaDocumento.tenant_id == tenant_id
        )
    )).scalars().first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    url = await storage.obter_data_uri(documento.chave_storage)
    if not url:
        raise HTTPException(status_code=404, detail="Ficheiro do documento já não está disponível.")
    return url


async def listar_matriculas_do_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> list[dict]:
    """Mostra todas as turmas e anos letivos pelos quais o aluno já passou na escola."""
    resultado = await db.execute(
        select(Matricula, Turma.nome_codigo).join(Turma, Turma.id == Matricula.turma_id).where(
            Matricula.aluno_id == aluno_id, Matricula.tenant_id == tenant_id
        )
    )
    return [
        {
            "matricula_id": matricula.id,
            "turma_id": matricula.turma_id,
            "nome_turma": nome_turma,
            "status_matricula": matricula.status_matricula,
            "ano_letivo": matricula.ano_letivo,
            "data_matricula": matricula.data_matricula,
        }
        for matricula, nome_turma in resultado.all()
    ]


# ==========================================
# REMATRÍCULA (ecrã dedicado — Secretaria/Gestor)
# ==========================================
async def _ano_letivo_corrente(db: AsyncSession, tenant_id) -> int | None:
    """Sem um "ano letivo corrente" explícito em Tenant, assume-se o
    ano letivo mais recente com pelo menos uma matrícula ATIVO — é o
    que faz sentido "renovar a partir dele" na prática."""
    return (await db.execute(
        select(func.max(Matricula.ano_letivo)).where(
            Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO"
        )
    )).scalar_one_or_none()


async def listar_candidatos_rematricula(db: AsyncSession, tenant_id, ano_letivo: int | None = None) -> dict:
    """Alunos com matrícula ATIVO no `ano_letivo` de origem (por omissão,
    o mais recente com matrículas ativas) que ainda não têm matrícula
    nenhuma no ano seguinte — candidatos a renovar. Para cada um,
    reaproveita a MESMA verificação de RN05 que criar_matricula vai
    aplicar de facto, e sinaliza se a família já confirmou interesse
    pelo Portal (ver cruds/portal.py::pedir_rematricula)."""
    ano_origem = ano_letivo if ano_letivo is not None else await _ano_letivo_corrente(db, tenant_id)
    if ano_origem is None:
        return {"ano_letivo_origem": None, "ano_letivo_destino": None, "candidatos": []}
    ano_destino = ano_origem + 1

    ja_renovados = set((await db.execute(
        select(Matricula.aluno_id).where(Matricula.tenant_id == tenant_id, Matricula.ano_letivo == ano_destino)
    )).scalars().all())

    pedidos_confirmados = set((await db.execute(
        select(PedidoRematricula.aluno_id).where(
            PedidoRematricula.tenant_id == tenant_id, PedidoRematricula.ano_letivo_destino == ano_destino
        )
    )).scalars().all())

    linhas = (await db.execute(
        select(Matricula, Aluno.nome_completo, Aluno.matricula_interna, Turma.nome_codigo)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .join(Turma, Turma.id == Matricula.turma_id)
        .where(Matricula.tenant_id == tenant_id, Matricula.ano_letivo == ano_origem, Matricula.status_matricula == "ATIVO")
        .order_by(Aluno.nome_completo)
    )).all()

    candidatos = []
    for matricula, nome_aluno, matricula_interna, nome_turma in linhas:
        if matricula.aluno_id in ja_renovados:
            continue
        candidatos.append({
            "aluno_id": matricula.aluno_id,
            "nome_completo": nome_aluno,
            "matricula_interna": matricula_interna,
            "matricula_atual_id": matricula.id,
            "turma_atual_id": matricula.turma_id,
            "nome_turma_atual": nome_turma,
            "bloqueado_por_atraso": await tem_mensalidade_em_atraso_de_ano_anterior(db, tenant_id, matricula.aluno_id, ano_destino),
            "pedido_confirmado_pela_familia": matricula.aluno_id in pedidos_confirmados,
        })

    return {"ano_letivo_origem": ano_origem, "ano_letivo_destino": ano_destino, "candidatos": candidatos}
