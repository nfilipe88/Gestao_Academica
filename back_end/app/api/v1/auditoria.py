"""Trilha de auditoria geral — quem/quando/o quê foi criado ou alterado
em qualquer entidade da própria escola. Gerada automaticamente (ver
app/core/auditoria.py), esta rota só lê. Só o Gestor: é informação
sensível sobre a atividade de todo o staff, mesmo alcance de
/api/v1/usuarios/auditoria (RBAC) — ver app/api/v1/admin.py para o
equivalente cross-tenant do Super Admin.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import auditoria as crud_auditoria

router = APIRouter(prefix="/api/v1/auditoria", tags=["Auditoria"])

_PODE_ACEDER = exigir_perfil("GESTOR")


@router.get("")
async def listar_auditoria(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    entidade: str | None = Query(None), entidade_id: str | None = Query(None),
    acao: str | None = Query(None), autor_id: uuid.UUID | None = Query(None),
    data_inicio: date | None = Query(None), data_fim: date | None = Query(None),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_auditoria.listar(
        db, utilizador["tenant_id"], page, page_size,
        entidade, entidade_id, acao, autor_id, data_inicio, data_fim
    )


@router.get("/entidades")
async def listar_entidades(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Nomes de tabela para povoar o filtro "Entidade" no frontend."""
    return await crud_auditoria.listar_entidades_distintas(db, utilizador["tenant_id"])
