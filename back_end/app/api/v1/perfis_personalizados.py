"""Perfis da escola (ex.: "Tesouraria") — o Gestor cria-os a partir da
Secretaria ou do Professor, com menos permissões. Ver
cruds/perfis_personalizados.py e app/core/mapa_permissoes.py.

Fora do Mapa de Permissões de propósito (tal como a Gestão de Acessos): só
o Gestor decide quem tem que poder na escola."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import exigir_perfil
from app.cruds import perfis_personalizados as crud
from app.database.session import obter_sessao_db
from app.schemas.permissoes import (
    PerfilPersonalizadoCreate, PerfilPersonalizadoOut, PerfilPersonalizadoRenomear, PermissaoPerfilEscolaUpdate,
)

router = APIRouter(prefix="/api/v1/perfis-personalizados", tags=["Perfis da Escola"])

_SO_GESTOR = exigir_perfil("GESTOR")


@router.get("", response_model=list[PerfilPersonalizadoOut])
async def listar(db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_GESTOR)):
    return await crud.listar(db, utilizador["tenant_id"])


@router.post("", response_model=PerfilPersonalizadoOut, status_code=status.HTTP_201_CREATED)
async def criar(dados: PerfilPersonalizadoCreate, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_GESTOR)):
    """Começa igual ao perfil base na escola; depois desmarca-se o que não deve ter."""
    return await crud.criar(db, utilizador["tenant_id"], dados.nome, dados.perfil_base)


@router.patch("/{perfil_id}", response_model=PerfilPersonalizadoOut)
async def renomear(perfil_id: uuid.UUID, dados: PerfilPersonalizadoRenomear,
                   db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_GESTOR)):
    return await crud.renomear(db, utilizador["tenant_id"], perfil_id, dados.nome)


@router.put("/{perfil_id}/permissoes", response_model=PerfilPersonalizadoOut)
async def atualizar_modulo(perfil_id: uuid.UUID, dados: PermissaoPerfilEscolaUpdate,
                           db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_GESTOR)):
    """As 4 operações de UM módulo — nunca acima do que o perfil base pode na escola."""
    return await crud.atualizar_modulo(db, utilizador["tenant_id"], perfil_id, dados.modulo, dados)


@router.delete("/{perfil_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar(perfil_id: uuid.UUID, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_SO_GESTOR)):
    """Quem o tinha volta ao perfil base."""
    await crud.apagar(db, utilizador["tenant_id"], perfil_id)
