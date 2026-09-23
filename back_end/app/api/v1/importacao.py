"""Importação de Dados Legados (mini-pauta MININED) — ver app/cruds/importacao.py."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.schemas.importacao import (
    DesfazerImportacaoResposta, ImportacaoMiniPautaConfirmar, ImportacaoMiniPautaResposta,
    LoteImportacaoOut, PreviewMiniPautaResposta
)
from app.cruds import importacao as crud_importacao

router = APIRouter(prefix="/api/v1/importacao", tags=["Importação de Dados Legados"])

# GESTOR-only — reshape do plantel/histórico académico da escola é a
# mesma classe de impacto de configuracoes.py/usuarios.py/eventos.py.
_PODE_IMPORTAR = exigir_perfil("GESTOR")


@router.post("/mini-pauta/preview", response_model=PreviewMiniPautaResposta)
async def pre_visualizar_mini_pauta(
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_IMPORTAR)
):
    """Só faz parsing do ficheiro e devolve o que foi detetado — nada é gravado na BD (ver docstring do crud)."""
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    return await crud_importacao.pre_visualizar_mini_pauta(
        db, utilizador["tenant_id"], ficheiro.filename or "mini-pauta.xlsx",
        ficheiro.content_type or "application/octet-stream", conteudo
    )


@router.post("/mini-pauta/confirmar", response_model=ImportacaoMiniPautaResposta, status_code=status.HTTP_201_CREATED)
async def confirmar_importacao_mini_pauta(
    dados: ImportacaoMiniPautaConfirmar,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_IMPORTAR)
):
    return await crud_importacao.confirmar_importacao_mini_pauta(db, utilizador, dados)


@router.get("/lotes", response_model=list[LoteImportacaoOut])
async def listar_lotes(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_IMPORTAR)
):
    return await crud_importacao.listar_lotes(db, utilizador["tenant_id"])


@router.post("/lotes/{lote_id}/desfazer", response_model=DesfazerImportacaoResposta)
async def desfazer_importacao(
    lote_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_IMPORTAR)
):
    return await crud_importacao.desfazer_importacao(db, utilizador, lote_id)
