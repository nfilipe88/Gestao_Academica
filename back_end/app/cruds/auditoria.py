from datetime import date, datetime, time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Usuario
from app.database.models_auditoria import AuditLog
from app.core.paginacao import DEFAULT_PAGE_SIZE, paginar_linhas


async def listar(
    db: AsyncSession, tenant_id: uuid.UUID, page: int, page_size: int = DEFAULT_PAGE_SIZE,
    entidade: str | None = None, entidade_id: str | None = None, acao: str | None = None,
    autor_id: uuid.UUID | None = None, data_inicio: date | None = None, data_fim: date | None = None,
) -> dict:
    query = (
        select(AuditLog, Usuario.nome_completo)
        .outerjoin(Usuario, Usuario.id == AuditLog.autor_id)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.criado_em.desc())
    )
    if entidade:
        query = query.where(AuditLog.entidade == entidade)
    if entidade_id:
        query = query.where(AuditLog.entidade_id == entidade_id)
    if acao:
        query = query.where(AuditLog.acao == acao)
    if autor_id:
        query = query.where(AuditLog.autor_id == autor_id)
    if data_inicio:
        query = query.where(AuditLog.criado_em >= datetime.combine(data_inicio, time.min))
    if data_fim:
        query = query.where(AuditLog.criado_em <= datetime.combine(data_fim, time.max))

    pagina = await paginar_linhas(db, query, page, page_size)
    pagina["items"] = [
        {
            "id": registo.id, "autor_id": registo.autor_id, "autor_nome": nome_autor,
            "autor_perfil": registo.autor_perfil, "acao": registo.acao,
            "entidade": registo.entidade, "entidade_id": registo.entidade_id,
            "alteracoes": registo.alteracoes, "criado_em": registo.criado_em,
        }
        for registo, nome_autor in pagina["items"]
    ]
    return pagina


async def listar_entidades_distintas(db: AsyncSession, tenant_id: uuid.UUID) -> list[str]:
    """Nomes de tabela que já têm pelo menos um registo de auditoria nesta escola — alimenta o filtro "Entidade" no frontend."""
    resultado = await db.execute(
        select(AuditLog.entidade).where(AuditLog.tenant_id == tenant_id).distinct().order_by(AuditLog.entidade)
    )
    return [linha[0] for linha in resultado.all()]
