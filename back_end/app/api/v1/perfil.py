"""
Área de Perfil — qualquer utilizador autenticado (GESTOR, SECRETARIA,
PROFESSOR, ALUNO, RESPONSAVEL, SUPER_ADMIN) vê/edita a própria conta.

Deliberadamente sem exigir_perfil: ao contrário de quase todos os
outros módulos, este não é restrito a nenhum subconjunto de perfis — só
exige um JWT válido (Depends(obter_utilizador_atual)), porque toda a
gente tem uma conta própria para gerir. Ver app/cruds/perfil.py.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import obter_utilizador_atual
from app.cruds import perfil as crud_perfil
from app.schemas.perfil import PerfilUpdate, AlterarSenhaIn

router = APIRouter(prefix="/api/v1/perfil", tags=["Perfil"])


@router.get("")
async def obter_perfil(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_perfil.obter_perfil(db, utilizador["tenant_id"], utilizador["usuario_id"])


@router.put("")
async def atualizar_perfil(
    dados: PerfilUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_perfil.atualizar_perfil(db, utilizador["tenant_id"], utilizador["usuario_id"], dados)


@router.post("/alterar-senha")
async def alterar_senha(
    dados: AlterarSenhaIn,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    await crud_perfil.alterar_senha(db, utilizador["tenant_id"], utilizador["usuario_id"], dados)
    return {"mensagem": "Palavra-passe alterada com sucesso."}


# ==========================================
# ASSINATURA PESSOAL (para documentos PDF emitidos pelo próprio, ver
# app/core/assinaturas.py) — carregada por upload ou desenhada num
# ecrã tátil pelo próprio frontend, que envia sempre uma imagem já
# pronta (PNG/JPEG/WebP), tal como o upload de ficheiro.
# ==========================================
@router.post("/assinatura", status_code=status.HTTP_201_CREATED)
async def enviar_assinatura_pessoal(
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    await crud_perfil.enviar_assinatura_pessoal(
        db, utilizador["tenant_id"], utilizador["usuario_id"],
        ficheiro.filename or "assinatura", ficheiro.content_type or "application/octet-stream", conteudo
    )
    return await crud_perfil.obter_perfil(db, utilizador["tenant_id"], utilizador["usuario_id"])


@router.get("/assinatura")
async def obter_assinatura_pessoal(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    """Devolve a assinatura pessoal ativa como data URI — pedida só quando aberta."""
    url = await crud_perfil.obter_assinatura_pessoal_url(db, utilizador["tenant_id"], utilizador["usuario_id"])
    return {"url": url}


@router.delete("/assinatura")
async def remover_assinatura_pessoal(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    await crud_perfil.remover_assinatura_pessoal(db, utilizador["tenant_id"], utilizador["usuario_id"])
    return await crud_perfil.obter_perfil(db, utilizador["tenant_id"], utilizador["usuario_id"])
