import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff, obter_utilizador_atual
from app.cruds import configuracoes as crud_configuracoes
from app.schemas.configuracoes import (
    ConfiguracaoTenantOut, ConfiguracaoTenantUpdate, TipoAvaliacaoCreate, TipoAvaliacaoOut, TipoAvaliacaoUpdate
)

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


# ==========================================
# LOGÓTIPO DA ESCOLA
# ==========================================
@router.get("/logotipo")
async def obter_logotipo(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    """Leitura aberta a qualquer autenticado do tenant (staff E Portal) —
    o logótipo é usado nos PDFs vistos também pelo Aluno/Responsável."""
    conteudo, content_type = await crud_configuracoes.obter_logotipo(db, utilizador["tenant_id"])
    return Response(content=conteudo, media_type=content_type)


@router.put("/logotipo", response_model=ConfiguracaoTenantOut)
async def atualizar_logotipo(
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_EDITAR)
):
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    return await crud_configuracoes.atualizar_logotipo(
        db, utilizador["tenant_id"], ficheiro.filename or "logotipo", ficheiro.content_type or "application/octet-stream", conteudo
    )


@router.delete("/logotipo", response_model=ConfiguracaoTenantOut)
async def remover_logotipo(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_EDITAR)
):
    return await crud_configuracoes.remover_logotipo(db, utilizador["tenant_id"])


# ==========================================
# TIPOS DE AVALIAÇÃO (catálogo por escola)
# ==========================================
@router.get("/tipos-avaliacao", response_model=list[TipoAvaliacaoOut])
async def listar_tipos_avaliacao(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(exigir_perfil_staff)
):
    """Leitura aberta a qualquer staff — o Professor precisa da lista para escolher o tipo ao criar uma Avaliação."""
    return await crud_configuracoes.listar_tipos_avaliacao(db, utilizador["tenant_id"])


@router.post("/tipos-avaliacao", response_model=TipoAvaliacaoOut, status_code=status.HTTP_201_CREATED)
async def criar_tipo_avaliacao(
    dados: TipoAvaliacaoCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_EDITAR)
):
    return await crud_configuracoes.criar_tipo_avaliacao(db, utilizador["tenant_id"], dados)


@router.put("/tipos-avaliacao/{tipo_id}", response_model=TipoAvaliacaoOut)
async def atualizar_tipo_avaliacao(
    tipo_id: uuid.UUID,
    dados: TipoAvaliacaoUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_EDITAR)
):
    return await crud_configuracoes.atualizar_tipo_avaliacao(db, utilizador["tenant_id"], tipo_id, dados)
