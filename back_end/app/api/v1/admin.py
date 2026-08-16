import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db_admin
from app.core.security import exigir_perfil
from app.schemas.admin import TenantStatusUpdate, ValidadeLicencaUpdate
from app.schemas.usuarios import AtivoUpdate, PerfilAcessoUpdate, SecretariaCreate
from app.cruds import admin as crud_admin
from app.cruds import usuarios as crud_usuarios


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
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Lista todas as instituições (tenants) da plataforma, com contagens básicas de uso."""
    return await crud_admin.listar_tenants(db, page, page_size)


@router.patch("/tenants/{tenant_id}/status")
async def atualizar_status_tenant(
    tenant_id: uuid.UUID,
    dados: TenantStatusUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Suspende ou reativa uma instituição — bloqueia/desbloqueia o login de todos os seus utilizadores."""
    tenant = await crud_admin.atualizar_status_tenant(db, tenant_id, dados)
    return {"mensagem": f"{tenant.nome_fantasia} agora está {tenant.status}.", "status": tenant.status}


@router.patch("/tenants/{tenant_id}/validade-licenca")
async def atualizar_validade_licenca(
    tenant_id: uuid.UUID,
    dados: ValidadeLicencaUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
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
    db: AsyncSession = Depends(obter_sessao_db_admin),
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


# ==========================================
# GESTÃO DE ACESSOS — cross-tenant (qualquer escola)
# ==========================================
# Mesmo crud usado por app/api/v1/usuarios.py (Gestor, só a própria
# escola) — aqui o tenant_id vem do path da URL em vez do token, é a
# única diferença.

@router.get("/tenants/{tenant_id}/usuarios")
async def listar_usuarios_do_tenant(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Staff (Gestor/Secretaria/Professor) de uma escola específica."""
    return await crud_usuarios.listar_usuarios(db, tenant_id, page, page_size)


@router.post("/tenants/{tenant_id}/usuarios/secretaria", status_code=201)
async def criar_secretaria_no_tenant(
    tenant_id: uuid.UUID, dados: SecretariaCreate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Cria uma conta de Secretaria numa escola específica (ex.: apoio ao onboarding)."""
    novo = await crud_usuarios.criar_secretaria(db, tenant_id, dados, utilizador["usuario_id"])
    return {"mensagem": f'Conta de Secretaria criada para "{novo.nome_completo}".', "id": novo.id}


@router.patch("/tenants/{tenant_id}/usuarios/{usuario_id}/perfil")
async def alterar_perfil_no_tenant(
    tenant_id: uuid.UUID, usuario_id: uuid.UUID, dados: PerfilAcessoUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Muda o perfil (Gestor/Secretaria) de um utilizador de qualquer escola."""
    alterado = await crud_usuarios.alterar_perfil(db, tenant_id, usuario_id, dados, utilizador["usuario_id"])
    return {"mensagem": f'"{alterado.nome_completo}" passou a ter o perfil {alterado.perfil_acesso}.', "perfil_acesso": alterado.perfil_acesso}


@router.patch("/tenants/{tenant_id}/usuarios/{usuario_id}/ativo")
async def alterar_estado_ativo_no_tenant(
    tenant_id: uuid.UUID, usuario_id: uuid.UUID, dados: AtivoUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Suspende ou reativa o acesso de UM utilizador de qualquer escola."""
    alterado = await crud_usuarios.alterar_estado_ativo(db, tenant_id, usuario_id, dados.ativo, utilizador["usuario_id"])
    return {"mensagem": f'"{alterado.nome_completo}" agora está {"ativo" if alterado.ativo else "suspenso"}.', "ativo": alterado.ativo}


@router.get("/tenants/{tenant_id}/usuarios/auditoria")
async def listar_auditoria_do_tenant(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Histórico de gestão de acessos de uma escola específica."""
    return await crud_usuarios.listar_auditoria(db, tenant_id, page, page_size)
