import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, obter_utilizador_atual
from app.cruds import permissoes as crud_permissoes
from app.schemas.permissoes import PerfilNomeOut, PerfilNomeUpdate, PermissaoModuloOut, PermissaoModuloUpdate

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
    """Super Admin: o mapa base. Gestor: o mapa base + o que vale na escola dele."""
    tenant_id = utilizador["tenant_id"] if utilizador["perfil_acesso"] == "GESTOR" else None
    return await crud_permissoes.listar_permissoes(db, tenant_id)


# Desde que o mapa decide o acesso: o mapa base é de todas as escolas (só o
# Super Admin); cada Gestor só restringe a própria escola.
_SO_SUPER_ADMIN_BASE = exigir_perfil("SUPER_ADMIN")
_SO_GESTOR = exigir_perfil("GESTOR")


@router.patch("/{permissao_id}", response_model=PermissaoModuloOut)
async def atualizar_permissao(
    permissao_id: uuid.UUID,
    dados: PermissaoModuloUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_SUPER_ADMIN_BASE)
):
    """Mapa base — vale para TODAS as escolas, por isso só o Super Admin."""
    return await crud_permissoes.atualizar_permissao(db, permissao_id, dados)


@router.put("/{permissao_id}/escola", response_model=PermissaoModuloOut)
async def restringir_na_escola(
    permissao_id: uuid.UUID,
    dados: PermissaoModuloUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_GESTOR)
):
    """Restrição da própria escola (Gestor) — só pode tirar ao mapa base."""
    return await crud_permissoes.restringir_na_escola(db, utilizador["tenant_id"], permissao_id, dados)



# ==========================================
# NOMES DOS PERFIS — o que as pessoas leem (GESTOR → "Diretor Geral").
# Ler: qualquer pessoa com sessão (aparecem em listas e mensagens de toda a
# app). Mudar: só o Super Admin, e vale para toda a plataforma.
# ==========================================
_SO_SUPER_ADMIN = exigir_perfil("SUPER_ADMIN")


@router.get("/perfis", response_model=list[PerfilNomeOut])
async def listar_nomes_perfis(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_permissoes.listar_nomes_perfis(db)


@router.put("/perfis/{codigo}", response_model=PerfilNomeOut)
async def renomear_perfil(
    codigo: str, dados: PerfilNomeUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_SUPER_ADMIN)
):
    """Muda só o nome mostrado; o código (e todas as permissões) fica igual."""
    return await crud_permissoes.renomear_perfil(db, codigo, dados.nome)
