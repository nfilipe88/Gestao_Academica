"""Eventos de segurança da própria escola — Gestor. O equivalente do Super
Admin (todas as escolas + IPs bloqueados) está em app/api/v1/admin.py."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import exigir_perfil
from app.cruds import seguranca as crud_seguranca
from app.database.session import obter_sessao_db
from app.schemas.comum import PaginaOut
from app.schemas.seguranca import EventoSegurancaOut

router = APIRouter(prefix="/api/v1/seguranca", tags=["Segurança"])

_PODE_VER = exigir_perfil("GESTOR")


@router.get("/eventos", response_model=PaginaOut[EventoSegurancaOut])
async def listar_eventos(
    tipo: str | None = Query(None, max_length=40), gravidade: str | None = Query(None, max_length=10),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_VER),
):
    """Tentativas de acesso indevido na própria escola (ex.: alguém sem
    permissão a tentar uma área reservada, ficheiro malicioso, palavras-
    passe erradas numa conta da escola)."""
    return await crud_seguranca.listar_eventos(
        db, tenant_id=utilizador["tenant_id"], so_da_escola=True, tipo=tipo, gravidade=gravidade,
        page=page, page_size=page_size,
    )
