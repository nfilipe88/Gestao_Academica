import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import propinas as crud_propinas
from app.schemas.propinas import LinhaPropina, PropinaUpdate

router = APIRouter(prefix="/api/v1/propinas", tags=["Tabela de Propinas"])

# Mesmo alcance do Financeiro (ver api/v1/financeiro.py) — o Professor
# não tem acesso a valores de propinas/mensalidades.
_PODE_ACEDER = exigir_perfil("GESTOR", "SECRETARIA")


@router.get("", response_model=list[LinhaPropina])
async def listar_propinas(
    ano_letivo: int = Query(..., ge=2000, le=2100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Uma linha por Curso/Série da escola — inclui séries sem preço ainda definido nesse ano letivo."""
    return await crud_propinas.listar_propinas(db, utilizador["tenant_id"], ano_letivo)


@router.put("/serie/{serie_ano_id}", response_model=LinhaPropina)
async def definir_propina(
    serie_ano_id: uuid.UUID, dados: PropinaUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_propinas.definir_propina(db, utilizador["tenant_id"], serie_ano_id, dados)


@router.delete("/{propina_id}", status_code=204)
async def apagar_propina(
    propina_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    await crud_propinas.apagar_propina(db, utilizador["tenant_id"], propina_id)
