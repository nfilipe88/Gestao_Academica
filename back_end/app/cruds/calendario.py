"""Calendário do ano letivo — ver app/database/models_academico.py::CalendarioLetivo."""
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_academico import CalendarioLetivo
from app.database.models_diario import PeriodoAvaliacao
from app.schemas.calendario import CalendarioCreate, CalendarioUpdate


def _estado(inicio: date | None, fim: date | None, hoje: date) -> str | None:
    if not inicio or not fim:
        return None
    if hoje < inicio:
        return "PROXIMO"
    return "DECORRER" if hoje <= fim else "TERMINADO"


def _serializar(c: CalendarioLetivo, hoje: date) -> dict:
    return {"id": c.id, "ano_letivo": c.ano_letivo, "tipo": c.tipo, "nome": c.nome, "data_inicio": c.data_inicio,
            "data_fim": c.data_fim, "observacoes": c.observacoes, "origem": "CALENDARIO",
            "estado": _estado(c.data_inicio, c.data_fim, hoje)}


async def listar_calendario(db: AsyncSession, tenant_id, ano_letivo: int) -> list[dict]:
    """Entradas do calendário do ano + os trimestres do Diário que já têm janela
    de datas (só leitura, para o calendário mostrar tudo num sítio)."""
    hoje = date.today()
    registos = (await db.execute(
        select(CalendarioLetivo).where(CalendarioLetivo.tenant_id == tenant_id, CalendarioLetivo.ano_letivo == ano_letivo)
    )).scalars().all()
    itens = [_serializar(c, hoje) for c in registos]

    nomes_ja_no_calendario = {c.nome.strip().lower() for c in registos if c.tipo == "PERIODO_LETIVO"}
    periodos = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id,
                                       PeriodoAvaliacao.data_inicio.is_not(None), PeriodoAvaliacao.data_fim.is_not(None))
    )).scalars().all()
    for p in periodos:
        if p.nome.strip().lower() in nomes_ja_no_calendario or p.data_inicio.year not in (ano_letivo, ano_letivo + 1):
            continue
        itens.append({"id": None, "ano_letivo": ano_letivo, "tipo": "PERIODO_LETIVO", "nome": p.nome, "data_inicio": p.data_inicio,
                      "data_fim": p.data_fim, "observacoes": "Definido no Diário de Classe", "origem": "DIARIO",
                      "estado": _estado(p.data_inicio, p.data_fim, hoje)})
    return sorted(itens, key=lambda i: (i["data_inicio"] or date.max, i["nome"]))


async def criar_entrada(db: AsyncSession, tenant_id, dados: CalendarioCreate) -> dict:
    nova = CalendarioLetivo(tenant_id=tenant_id, **dados.model_dump())
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return _serializar(nova, date.today())


async def _obter(db: AsyncSession, tenant_id, entrada_id: uuid.UUID) -> CalendarioLetivo:
    entrada = (await db.execute(
        select(CalendarioLetivo).where(CalendarioLetivo.id == entrada_id, CalendarioLetivo.tenant_id == tenant_id)
    )).scalars().first()
    if not entrada:
        raise HTTPException(status_code=404, detail="Entrada do calendário não encontrada.")
    return entrada


async def atualizar_entrada(db: AsyncSession, tenant_id, entrada_id: uuid.UUID, dados: CalendarioUpdate) -> dict:
    entrada = await _obter(db, tenant_id, entrada_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(entrada, campo, valor)
    if entrada.data_inicio > entrada.data_fim:
        raise HTTPException(status_code=400, detail="A data de início não pode ser depois da data de fim.")
    await db.commit()
    await db.refresh(entrada)
    return _serializar(entrada, date.today())


async def remover_entrada(db: AsyncSession, tenant_id, entrada_id: uuid.UUID) -> None:
    await db.delete(await _obter(db, tenant_id, entrada_id))
    await db.commit()
