import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_permissoes import PermissaoModulo
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
