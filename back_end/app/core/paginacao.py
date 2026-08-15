"""
Paginação (LIMIT/OFFSET) para as listagens que podem crescer sem
limite com o tamanho da escola (Alunos, Professores, Comunicados, ...)
— uma escola com centenas de alunos não pode continuar a receber a
tabela inteira numa única resposta.

Convenção usada em toda a API: `page` (1-based) e `page_size`
(1–100, omitido = DEFAULT_PAGE_SIZE) como query params; a resposta
vem sempre embrulhada em {items, total, page, page_size, total_pages}
em vez de uma lista nua — isto é uma mudança de contrato deliberada
para estas rotas (o frontend já espera o envelope, ver
shared/pagination nos componentes Angular).
"""
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

DEFAULT_PAGE_SIZE = 25
PAGE_SIZES_VALIDOS = {10, 25, 50, 100}


async def paginar(db: AsyncSession, query: Select, page: int, page_size: int) -> dict:
    """
    `query` é um select() já filtrado e ordenado, mas SEM limit/offset.
    Devolve o envelope padrão; `items` fica com os objetos/linhas
    devolvidos por `.scalars().all()` (a maioria dos casos desta API,
    que faz select() de uma única entidade) — quem chamar com uma
    query de múltiplas colunas usa paginar_linhas() abaixo em vez desta.
    """
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    pagina = (await db.execute(query.limit(page_size).offset((page - 1) * page_size))).scalars().all()
    return {
        "items": pagina,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


async def paginar_linhas(db: AsyncSession, query: Select, page: int, page_size: int) -> dict:
    """Como paginar(), mas para queries de múltiplas colunas — devolve as Row (tuplas) de `.all()`, não `.scalars().all()`."""
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    pagina = (await db.execute(query.limit(page_size).offset((page - 1) * page_size))).all()
    return {
        "items": pagina,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }
