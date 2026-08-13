"""Acesso a dados e regras de negócio (RN01-RN05) de Matrículas."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
import uuid

from app.database.models_academico import Turma
from app.database.models_pessoas import Aluno
from app.database.models_matricula import Matricula
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade
from app.schemas.matriculas import MatriculaCreate, MatriculaStatusUpdate

ESTADOS_VALIDOS = {"ATIVO", "TRANSFERIDO", "TRANCADO", "EVADIDO"}


# ==========================================
# RN05 do Financeiro (Nível 2) — Bloqueios Legais
# ==========================================
# "Por regras governamentais [...] um aluno inadimplente não pode ser
# impedido de frequentar aulas [...] durante o ano letivo em curso [...]
# O bloqueio real só ocorre na tentativa de Renovação de Matrícula para
# o ano seguinte." — por isso o bloqueio vive aqui (criar_matricula),
# não em lado nenhum do módulo académico do dia a dia (Diário de
# Classe, etc. continuam sempre acessíveis).
async def _tem_mensalidade_em_atraso_de_ano_anterior(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, ano_letivo_novo: int) -> bool:
    """
    Só bloqueia se isto for de facto uma RENOVAÇÃO: o aluno já teve
    matrícula num ano letivo anterior, e essa matrícula tem um
    Contrato_Financeiro com pelo menos uma Fatura_Mensalidade
    verdadeiramente em atraso (pendente e já passada a data de
    vencimento) — o cálculo de juros/multa em si (RN02) é irrelevante
    aqui, só interessa o facto de estar por pagar.
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
    if await _tem_mensalidade_em_atraso_de_ano_anterior(db, tenant_id, dados.aluno_id, dados.ano_letivo):
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
    """Atualiza a situação do aluno (ex: de Ativo para Trancado, Transferido ou Evadido)."""
    if dados.status_matricula not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Use um de: {', '.join(sorted(ESTADOS_VALIDOS))}."
        )

    matricula = (await db.execute(
        select(Matricula).where(Matricula.id == matricula_id, Matricula.tenant_id == tenant_id)
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada na sua instituição.")

    matricula.status_matricula = dados.status_matricula
    await db.commit()


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
