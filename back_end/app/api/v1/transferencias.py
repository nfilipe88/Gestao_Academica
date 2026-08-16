import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import transferencias as crud_transferencias
from app.schemas.transferencias import RejeitarTransferenciaRequest, SolicitacaoTransferenciaCreate

router = APIRouter(prefix="/api/v1/transferencias", tags=["Transferência de Alunos"])

_PODE_PEDIR = exigir_perfil("GESTOR", "SECRETARIA")
_PODE_DECIDIR = exigir_perfil("SUPER_ADMIN")


@router.post("")
async def criar_solicitacao(
    dados: SolicitacaoTransferenciaCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_PEDIR)
):
    return await crud_transferencias.criar_solicitacao(db, utilizador["tenant_id"], utilizador, dados)


@router.get("/minhas")
async def listar_minhas_solicitacoes(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None), data_inicio: date | None = Query(None), data_fim: date | None = Query(None),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_PEDIR)
):
    return await crud_transferencias.listar_minhas_solicitacoes(
        db, utilizador["tenant_id"], page, page_size, status, data_inicio, data_fim
    )


@router.get("")
async def listar_solicitacoes_super_admin(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_DECIDIR)
):
    return await crud_transferencias.listar_solicitacoes_super_admin(db, page, page_size)


@router.patch("/{solicitacao_id}/aprovar")
async def aprovar_e_migrar(
    solicitacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_DECIDIR)
):
    return await crud_transferencias.aprovar_e_migrar(db, solicitacao_id)


@router.patch("/{solicitacao_id}/rejeitar")
async def rejeitar(
    solicitacao_id: uuid.UUID, dados: RejeitarTransferenciaRequest,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_DECIDIR)
):
    return await crud_transferencias.rejeitar(db, solicitacao_id, dados)
