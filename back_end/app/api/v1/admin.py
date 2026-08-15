import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.schemas.admin import TenantStatusUpdate, ValidadeLicencaUpdate
from app.cruds import admin as crud_admin


async def _via_background_tasks(background_tasks: BackgroundTasks):
    """Fábrica do `agendar_email` esperado pelo crud — despacha via BackgroundTasks.add_task."""
    async def agendar(func, **kwargs):
        background_tasks.add_task(func, **kwargs)
    return agendar

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


@router.patch("/tenants/{tenant_id}/validade-licenca")
async def atualizar_validade_licenca(
    tenant_id: uuid.UUID,
    dados: ValidadeLicencaUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Define a data de validade da licença — o scheduler alerta e suspende automaticamente ao expirar."""
    tenant = await crud_admin.atualizar_validade_licenca(db, tenant_id, dados)
    return {
        "mensagem": f"Validade da licença de {tenant.nome_fantasia} atualizada.",
        "data_validade_licenca": tenant.data_validade_licenca
    }


@router.post("/validade-licenca/processar")
async def processar_validade_licencas(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """
    Disparo manual do alerta/suspensão automática por validade de
    licença — útil para testar já; o job diário em
    app/core/scheduler.py já corre isto sozinho, todos os dias às 07:00.
    """
    agendar_email = await _via_background_tasks(background_tasks)
    resumo = await crud_admin.processar_validade_licencas(db, agendar_email)
    return {"mensagem": "Validade de licenças processada.", **resumo}
