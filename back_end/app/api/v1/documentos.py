import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, obter_utilizador_atual
from app.cruds import documentos as crud_documentos
from app.schemas.documentos import (
    EntregarFisicoRequest, PrecoDocumentoUpdate, ResponderSolicitacaoEscolaRequest,
    SolicitacaoDocumentoEmissaoCreate, SolicitacaoDocumentoEscolaCreate,
)

router = APIRouter(prefix="/api/v1/documentos", tags=["Solicitações de Documentos"])

_PODE_GERIR_PRECOS = exigir_perfil("GESTOR")
_PODE_PEDIR = exigir_perfil("ALUNO", "RESPONSAVEL")
_PODE_GERIR_STAFF = exigir_perfil("GESTOR", "SECRETARIA")


# ==========================================
# A. TABELA DE PREÇOS
# ==========================================
@router.get("/precos")
async def listar_precos(db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_PRECOS)):
    return await crud_documentos.listar_precos(db, utilizador["tenant_id"])


@router.put("/precos/{tipo_documento}")
async def atualizar_preco(
    tipo_documento: str, dados: PrecoDocumentoUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_PRECOS)
):
    return await crud_documentos.atualizar_preco(db, utilizador["tenant_id"], tipo_documento, dados)


# ==========================================
# B. PEDIDOS DE EMISSÃO (Aluno/Responsável -> Escola)
# ==========================================
@router.post("/solicitacoes")
async def criar_solicitacao_emissao(
    dados: SolicitacaoDocumentoEmissaoCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_PEDIR)
):
    return await crud_documentos.criar_solicitacao_emissao(db, utilizador["tenant_id"], utilizador, dados)


@router.get("/solicitacoes/minhas")
async def listar_minhas_solicitacoes_emissao(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_PEDIR)
):
    return await crud_documentos.listar_minhas_solicitacoes_emissao(db, utilizador["tenant_id"], utilizador)


@router.get("/solicitacoes")
async def listar_solicitacoes_emissao_staff(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_STAFF)
):
    return await crud_documentos.listar_solicitacoes_emissao_staff(db, utilizador["tenant_id"], page, page_size)


@router.post("/solicitacoes/{solicitacao_id}/gerar-cobranca")
async def gerar_cobranca_documento(
    solicitacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_documentos.gerar_cobranca_documento(db, utilizador["tenant_id"], solicitacao_id, utilizador)


@router.post("/solicitacoes/capturar")
async def capturar_pagamento_documento(
    order_id: str,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_documentos.capturar_pagamento_documento(db, utilizador["tenant_id"], order_id, utilizador)


@router.get("/solicitacoes/{solicitacao_id}/pdf")
async def descarregar_pdf_solicitacao(
    solicitacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    pdf_bytes = await crud_documentos.gerar_pdf_solicitacao(db, utilizador["tenant_id"], solicitacao_id, utilizador)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="documento-{solicitacao_id}.pdf"'}
    )


@router.patch("/solicitacoes/{solicitacao_id}/entregar-fisico")
async def marcar_entrega_fisica(
    solicitacao_id: uuid.UUID, dados: EntregarFisicoRequest,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_STAFF)
):
    return await crud_documentos.marcar_entrega_fisica(db, utilizador["tenant_id"], solicitacao_id, dados)


@router.patch("/solicitacoes/{solicitacao_id}/cancelar")
async def cancelar_solicitacao_emissao(
    solicitacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_STAFF)
):
    return await crud_documentos.cancelar_solicitacao_emissao(db, utilizador["tenant_id"], solicitacao_id)


# ==========================================
# C. PEDIDOS DA ESCOLA (Escola -> Aluno/Responsável/Professor)
# ==========================================
@router.post("/pedidos-escola")
async def criar_solicitacao_escola(
    dados: SolicitacaoDocumentoEscolaCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_STAFF)
):
    return await crud_documentos.criar_solicitacao_escola(db, utilizador["tenant_id"], utilizador, dados)


@router.get("/pedidos-escola")
async def listar_solicitacoes_escola_staff(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_STAFF)
):
    return await crud_documentos.listar_solicitacoes_escola_staff(db, utilizador["tenant_id"], page, page_size)


@router.get("/pedidos-escola/minhas")
async def listar_minhas_solicitacoes_escola(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_documentos.listar_minhas_solicitacoes_escola(db, utilizador["tenant_id"], utilizador)


@router.patch("/pedidos-escola/{solicitacao_id}/responder")
async def responder_solicitacao_escola(
    solicitacao_id: uuid.UUID, dados: ResponderSolicitacaoEscolaRequest,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_documentos.responder_solicitacao_escola(db, utilizador["tenant_id"], utilizador, solicitacao_id, dados)


@router.patch("/pedidos-escola/{solicitacao_id}/concluir")
async def concluir_solicitacao_escola(
    solicitacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR_STAFF)
):
    return await crud_documentos.concluir_solicitacao_escola(db, utilizador["tenant_id"], solicitacao_id)
