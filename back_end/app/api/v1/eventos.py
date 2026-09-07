import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.schemas.eventos import EventoCreate, EventoOut, EventoUpdate
from app.cruds import eventos as crud_eventos

router = APIRouter(prefix="/api/v1/eventos", tags=["Eventos"])

# GESTOR-only, mesmo critério do Site Público (marketing/página
# pública da escola) — sem gate de módulo SaaS em main.py, também como
# o Site Público: não é um módulo académico "premium", é parte da
# presença pública da escola.
_PODE_GERIR = exigir_perfil("GESTOR")


@router.get("", response_model=list[EventoOut])
async def listar_eventos(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Todos os eventos da escola, publicados ou não."""
    return await crud_eventos.listar_eventos(db, utilizador["tenant_id"])


@router.post("", response_model=EventoOut, status_code=status.HTTP_201_CREATED)
async def criar_evento(
    dados: EventoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    return await crud_eventos.criar_evento(db, utilizador["tenant_id"], dados)


@router.patch("/{evento_id}", response_model=EventoOut)
async def atualizar_evento(
    evento_id: uuid.UUID,
    dados: EventoUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    return await crud_eventos.atualizar_evento(db, utilizador["tenant_id"], evento_id, dados)


@router.delete("/{evento_id}")
async def remover_evento(
    evento_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    await crud_eventos.remover_evento(db, utilizador["tenant_id"], evento_id)
    return {"mensagem": "Evento removido."}


@router.post("/{evento_id}/fotos", response_model=EventoOut, status_code=status.HTTP_201_CREATED)
async def adicionar_foto_evento(
    evento_id: uuid.UUID,
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    return await crud_eventos.adicionar_foto_evento(
        db, utilizador["tenant_id"], evento_id,
        ficheiro.filename or "foto", ficheiro.content_type or "application/octet-stream", conteudo
    )


@router.delete("/{evento_id}/fotos/{foto_id}", response_model=EventoOut)
async def remover_foto_evento(
    evento_id: uuid.UUID,
    foto_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    return await crud_eventos.remover_foto_evento(db, utilizador["tenant_id"], evento_id, foto_id)
