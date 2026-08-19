import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_academico import Curso, SerieAno
from app.database.models_propinas import PropinaSerie
from app.schemas.propinas import PropinaUpdate


async def listar_propinas(db: AsyncSession, tenant_id: uuid.UUID, ano_letivo: int) -> list[dict]:
    """Uma linha por Série/Ano da escola, com o valor desse ano letivo se
    já estiver definido — devolve TODAS as séries (mesmo sem preço
    ainda) para a equipa preencher, não só as que já têm valor."""
    linhas = (await db.execute(
        select(
            Curso.id, Curso.nome, SerieAno.id, SerieAno.nome,
            PropinaSerie.id, PropinaSerie.valor_mensalidade, PropinaSerie.valor_matricula
        )
        .select_from(Curso)
        .join(SerieAno, SerieAno.curso_id == Curso.id)
        .outerjoin(
            PropinaSerie,
            (PropinaSerie.serie_ano_id == SerieAno.id) & (PropinaSerie.ano_letivo == ano_letivo)
        )
        .where(Curso.tenant_id == tenant_id)
        .order_by(Curso.nome, SerieAno.nome)
    )).all()

    return [
        {
            "curso_id": curso_id, "curso_nome": curso_nome,
            "serie_ano_id": serie_id, "serie_ano_nome": serie_nome,
            "propina_id": propina_id, "ano_letivo": ano_letivo,
            "valor_mensalidade": valor_mensalidade, "valor_matricula": valor_matricula,
        }
        for curso_id, curso_nome, serie_id, serie_nome, propina_id, valor_mensalidade, valor_matricula in linhas
    ]


async def definir_propina(
    db: AsyncSession, tenant_id: uuid.UUID, serie_ano_id: uuid.UUID, dados: PropinaUpdate
) -> dict:
    """Upsert: define (ou atualiza) o valor da propina de uma série num
    ano letivo. Repetir o mesmo valor em todas as séries de um curso é
    o equivalente a "preço por curso"; valores diferentes por série dão
    o "preço por classe" — o mesmo modelo cobre os dois pedidos."""
    serie = (await db.execute(
        select(SerieAno).where(SerieAno.id == serie_ano_id, SerieAno.tenant_id == tenant_id)
    )).scalars().first()
    if not serie:
        raise HTTPException(status_code=404, detail="Série/Ano não encontrada nesta escola.")

    existente = (await db.execute(
        select(PropinaSerie).where(
            PropinaSerie.serie_ano_id == serie_ano_id, PropinaSerie.ano_letivo == dados.ano_letivo
        )
    )).scalars().first()

    if existente:
        existente.valor_mensalidade = dados.valor_mensalidade
        existente.valor_matricula = dados.valor_matricula
        propina = existente
    else:
        propina = PropinaSerie(
            tenant_id=tenant_id, serie_ano_id=serie_ano_id, ano_letivo=dados.ano_letivo,
            valor_mensalidade=dados.valor_mensalidade, valor_matricula=dados.valor_matricula,
        )
        db.add(propina)
    await db.commit()
    await db.refresh(propina)

    curso_nome = (await db.execute(select(Curso.nome).where(Curso.id == serie.curso_id))).scalar_one()
    return {
        "curso_id": serie.curso_id, "curso_nome": curso_nome, "serie_ano_id": serie.id, "serie_ano_nome": serie.nome,
        "propina_id": propina.id, "ano_letivo": propina.ano_letivo,
        "valor_mensalidade": propina.valor_mensalidade, "valor_matricula": propina.valor_matricula,
    }


async def apagar_propina(db: AsyncSession, tenant_id: uuid.UUID, propina_id: uuid.UUID) -> None:
    propina = (await db.execute(
        select(PropinaSerie).where(PropinaSerie.id == propina_id, PropinaSerie.tenant_id == tenant_id)
    )).scalars().first()
    if not propina:
        raise HTTPException(status_code=404, detail="Propina não encontrada nesta escola.")
    await db.delete(propina)
    await db.commit()


def ano_letivo_atual() -> int:
    """Ano civil corrente — mesmo critério simples já usado noutros
    sítios da app (ex.: criar Turma) para sugerir o ano letivo por omissão."""
    return date.today().year
