"""Consulta dos eventos de segurança (o registo em si vive em
app/core/eventos_seguranca.py). O Gestor vê os da própria escola (filtro
explícito + RLS); o Super Admin vê todos, incluindo os anónimos."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import eventos_seguranca
from app.core.paginacao import paginar_linhas
from app.database.models import Tenant
from app.database.models_usuarios import EventoSeguranca


async def listar_eventos(
    db: AsyncSession, *, tenant_id=None, so_da_escola: bool, tipo: str | None = None,
    gravidade: str | None = None, ip: str | None = None, page: int = 1, page_size: int = 25,
) -> dict:
    query = (
        select(EventoSeguranca, Tenant.nome_fantasia)
        .outerjoin(Tenant, Tenant.id == EventoSeguranca.tenant_id)
        .order_by(EventoSeguranca.data_evento.desc())
    )
    if so_da_escola or tenant_id:
        query = query.where(EventoSeguranca.tenant_id == tenant_id)
    if tipo:
        query = query.where(EventoSeguranca.tipo == tipo)
    if gravidade:
        query = query.where(EventoSeguranca.gravidade == gravidade)
    if ip:
        query = query.where(EventoSeguranca.ip == ip.strip())

    pagina = await paginar_linhas(db, query, page, page_size)
    pagina["items"] = [
        {
            "id": e.id, "data_evento": e.data_evento, "tipo": e.tipo, "gravidade": e.gravidade, "ip": e.ip,
            "user_agent": e.user_agent, "email": e.email, "metodo": e.metodo, "caminho": e.caminho,
            "detalhe": e.detalhe, "tenant_id": e.tenant_id,
            "nome_escola": None if so_da_escola else nome_escola,
        }
        for e, nome_escola in pagina["items"]
    ]
    return pagina


async def listar_bloqueios() -> list[dict]:
    return [
        {"ip": b["ip"], "ate": datetime.fromtimestamp(b["ate"], tz=timezone.utc), "motivo": b["motivo"]}
        for b in await eventos_seguranca.listar_bloqueios()
    ]
