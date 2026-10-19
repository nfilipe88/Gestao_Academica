import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import nomes_perfil
from app.database.models_permissoes import PerfilNome, PermissaoModulo
from app.schemas.permissoes import PermissaoModuloUpdate


async def listar_permissoes(db: AsyncSession) -> list[PermissaoModulo]:
    """Mapa completo (todos os módulos x todos os perfis) — tabela global, sem tenant_id."""
    resultado = await db.execute(
        select(PermissaoModulo).order_by(PermissaoModulo.ordem, PermissaoModulo.perfil)
    )
    return resultado.scalars().all()


async def atualizar_permissao(
    db: AsyncSession, permissao_id: uuid.UUID, dados: PermissaoModuloUpdate
) -> PermissaoModulo:
    permissao = (
        await db.execute(select(PermissaoModulo).where(PermissaoModulo.id == permissao_id))
    ).scalars().first()
    if not permissao:
        raise HTTPException(status_code=404, detail="Célula do mapa de permissões não encontrada.")

    permissao.pode_criar = dados.pode_criar
    permissao.pode_ler = dados.pode_ler
    permissao.pode_atualizar = dados.pode_atualizar
    permissao.pode_apagar = dados.pode_apagar
    await db.commit()
    await db.refresh(permissao)
    return permissao


# ==========================================
# NOMES DOS PERFIS (ver models_permissoes.py::PerfilNome)
# ==========================================
async def listar_nomes_perfis(db: AsyncSession) -> list[PerfilNome]:
    return list((await db.execute(select(PerfilNome).order_by(PerfilNome.ordem))).scalars().all())


async def renomear_perfil(db: AsyncSession, codigo: str, nome: str) -> PerfilNome:
    perfil = await db.get(PerfilNome, codigo)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    nome = " ".join(nome.split())
    if len(nome) < 2:
        raise HTTPException(status_code=400, detail="O nome tem de ter pelo menos 2 caracteres.")
    repetido = (await db.execute(
        select(PerfilNome).where(func.lower(PerfilNome.nome) == nome.lower(), PerfilNome.codigo != codigo)
    )).scalars().first()
    if repetido:
        # Dois perfis com o mesmo nome tornavam impossível saber quem é quem nas listas.
        raise HTTPException(status_code=400, detail=f'O nome "{nome}" já é usado pelo perfil {repetido.codigo}.')
    perfil.nome = nome
    await db.commit()
    await db.refresh(perfil)
    nomes_perfil.invalidar()
    return perfil
