from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, obter_utilizador_atual
from app.cruds import configuracoes as crud_configuracoes
from app.schemas.configuracoes import ConfiguracaoTenantOut, ConfiguracaoTenantUpdate

router = APIRouter(prefix="/api/v1/configuracoes", tags=["Configurações da Escola"])

_PODE_EDITAR = exigir_perfil("GESTOR")


@router.get("", response_model=ConfiguracaoTenantOut)
async def obter_configuracao(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    """
    Leitura aberta a qualquer utilizador autenticado do tenant (staff E
    Portal) — a moeda configurada aqui é usada para formatar todos os
    valores monetários da plataforma, incluindo os que o Aluno/
    Responsável vê no Portal, por isso não pode ficar restrita ao GESTOR.
    """
    return await crud_configuracoes.obter_configuracao(db, utilizador["tenant_id"])


@router.put("", response_model=ConfiguracaoTenantOut)
async def atualizar_configuracao(
    dados: ConfiguracaoTenantUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_EDITAR)
):
    return await crud_configuracoes.atualizar_configuracao(db, utilizador["tenant_id"], dados)
