import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import exigir_perfil, obter_utilizador_atual
from app.cruds import calendario as crud
from app.database.session import obter_sessao_db
from app.schemas.calendario import CalendarioCreate, CalendarioOut, CalendarioUpdate

router = APIRouter(prefix="/api/v1/calendario", tags=["Calendário Letivo"])

_PODE_GERIR = exigir_perfil("GESTOR")


@router.get("", response_model=list[CalendarioOut])
async def listar_calendario(
    ano_letivo: int = Query(..., ge=2000, le=2100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual),
):
    """Qualquer utilizador da escola (staff e Portal) vê o calendário do ano; só o Gestor o edita."""
    return await crud.listar_calendario(db, utilizador["tenant_id"], ano_letivo)


@router.post("", response_model=CalendarioOut, status_code=status.HTTP_201_CREATED)
async def criar_entrada(dados: CalendarioCreate, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)):
    return await crud.criar_entrada(db, utilizador["tenant_id"], dados)


@router.patch("/{entrada_id}", response_model=CalendarioOut)
async def atualizar_entrada(entrada_id: uuid.UUID, dados: CalendarioUpdate,
                            db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)):
    return await crud.atualizar_entrada(db, utilizador["tenant_id"], entrada_id, dados)


@router.delete("/{entrada_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_entrada(entrada_id: uuid.UUID, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)):
    await crud.remover_entrada(db, utilizador["tenant_id"], entrada_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
