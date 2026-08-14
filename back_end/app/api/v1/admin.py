import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.schemas.admin import TenantStatusUpdate
from app.cruds import admin as crud_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Painel Super Admin"])

# Único perfil que existe fora do contexto de uma escola cliente — gere
# as instituições em si, não os dados académicos de nenhuma delas.
_PODE_ACEDER = exigir_perfil("SUPER_ADMIN")


@router.get("/tenants")
async def listar_tenants(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Lista todas as instituições (tenants) da plataforma, com contagens básicas de uso."""
    return await crud_admin.listar_tenants(db)


@router.patch("/tenants/{tenant_id}/status")
async def atualizar_status_tenant(
    tenant_id: uuid.UUID,
    dados: TenantStatusUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Suspende ou reativa uma instituição — bloqueia/desbloqueia o login de todos os seus utilizadores."""
    tenant = await crud_admin.atualizar_status_tenant(db, tenant_id, dados)
    return {"mensagem": f"{tenant.nome_fantasia} agora está {tenant.status}.", "status": tenant.status}
