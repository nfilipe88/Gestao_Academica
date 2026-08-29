"""Endpoints do site público (landing, preços) — sem autenticação.
Mesmo prefixo /api/v1/public já usado pela captação de Lead (ver
app/api/v1/crm.py::router_publico), mas ficheiro próprio por ser um
domínio diferente (planos comerciais, não CRM).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db_publica
from app.cruds import admin as crud_admin
from app.schemas.publico import PlanoSaaSPublicoOut

router = APIRouter(prefix="/api/v1/public", tags=["Público"])


@router.get("/planos", response_model=list[PlanoSaaSPublicoOut])
async def listar_planos_publicos(db: AsyncSession = Depends(obter_sessao_db_publica)):
    """Planos ativos, para a página de Preços — resposta explicitamente
    tipada (response_model) para garantir que nenhum dado interno de
    gestão escapa por engano, ao contrário do endpoint equivalente do
    Super Admin que devolve os objetos ORM diretamente."""
    return await crud_admin.listar_planos_publicos(db)
