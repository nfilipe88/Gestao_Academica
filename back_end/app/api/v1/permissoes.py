import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import permissoes as crud_permissoes
from app.schemas.permissoes import PermissaoModuloOut, PermissaoModuloUpdate

router = APIRouter(prefix="/api/v1/permissoes", tags=["Mapa de Permissões"])

# Tabela global (sem tenant_id, sem RLS — ver models_permissoes.py), por
# isso usa a sessão normal (obter_sessao_db) e não obter_sessao_db_admin:
# essa exige SUPER_ADMIN logo na dependency, o que bloquearia sempre o
# GESTOR. Aqui o RBAC fica só no exigir_perfil abaixo.
_PODE_ACEDER = exigir_perfil("SUPER_ADMIN", "GESTOR")


@router.get("", response_model=list[PermissaoModuloOut])
async def listar_permissoes(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_permissoes.listar_permissoes(db)


@router.patch("/{permissao_id}", response_model=PermissaoModuloOut)
async def atualizar_permissao(
    permissao_id: uuid.UUID,
    dados: PermissaoModuloUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_permissoes.atualizar_permissao(db, permissao_id, dados)
