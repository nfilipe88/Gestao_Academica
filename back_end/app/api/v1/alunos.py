from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.core.email import enviar_email, template_base
from app.core import fila_notificacoes
from app.schemas.alunos import AlunoCreate, CriarAcessoRequest, ResponsavelCreate, VincularResponsavel
from app.cruds import alunos as crud_alunos

router = APIRouter(prefix="/api/v1", tags=["Alunos e Responsáveis"])

# Quem pode cadastrar/vincular alunos e responsáveis (RBAC) — leitura
# fica aberta a qualquer funcionário da escola (exigir_perfil_staff).
# ALUNO/RESPONSAVEL usam antes o Portal (app/api/v1/portal.py).
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# ROTAS PARA ALUNOS
# ==========================================
@router.post("/alunos", status_code=status.HTTP_201_CREATED)
async def criar_aluno(
    dados: AlunoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria um novo aluno na escola do utilizador logado."""
    return await crud_alunos.criar_aluno(db, utilizador["tenant_id"], dados)

@router.get("/alunos")
async def listar_alunos(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    busca: str | None = Query(None, description="Filtra por nome, matrícula ou nº de documento (parcial)."),
    data_nascimento_inicio: date | None = Query(None),
    data_nascimento_fim: date | None = Query(None),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os alunos da escola do utilizador logado, paginados e opcionalmente filtrados."""
    return await crud_alunos.listar_alunos(
        db, utilizador["tenant_id"], page, page_size, busca, data_nascimento_inicio, data_nascimento_fim
    )

# ==========================================
# ROTAS PARA RESPONSÁVEIS
# ==========================================
@router.post("/responsaveis", status_code=status.HTTP_201_CREATED)
async def criar_responsavel(
    dados: ResponsavelCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria um novo responsável (Pai/Mãe/Tutor) na escola do utilizador logado."""
    return await crud_alunos.criar_responsavel(db, utilizador["tenant_id"], dados)

@router.get("/responsaveis")
async def listar_responsaveis(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os responsáveis da escola do utilizador logado, paginados."""
    return await crud_alunos.listar_responsaveis(db, utilizador["tenant_id"], page, page_size)

# ==========================================
# VÍNCULO ALUNO <-> RESPONSÁVEL
# ==========================================
@router.post("/alunos/{aluno_id}/responsaveis", status_code=status.HTTP_201_CREATED)
async def vincular_responsavel(
    aluno_id: uuid.UUID,
    dados: VincularResponsavel,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Vincula um responsável já existente a um aluno (RN: um aluno pode ter vários responsáveis)."""
    vinculo, aluno, responsavel = await crud_alunos.vincular_responsavel(db, utilizador["tenant_id"], aluno_id, dados)

    # E-mail de notificação (best-effort, via fila). Só envia se o
    # responsável tiver um e-mail registado — é opcional no cadastro.
    if responsavel.email:
        await fila_notificacoes.agendar_email(
            enviar_email,
            destinatario=responsavel.email,
            assunto=f"Foi associado(a) como responsável de {aluno.nome_completo}",
            corpo_html=template_base(
                "Novo vínculo registado",
                f"""
                <p>Olá {responsavel.nome_completo},</p>
                <p>Foi registado(a) como <strong>{dados.tipo_parentesco}</strong> de
                <strong>{aluno.nome_completo}</strong> (matrícula {aluno.matricula_interna})
                na plataforma de Gestão Académica.</p>
                {"<p>Ficou também identificado(a) como <strong>responsável financeiro</strong> deste aluno.</p>" if dados.responsavel_financeiro else ""}
                """
            )
        )

    return {"mensagem": "Responsável vinculado com sucesso", "id": vinculo.id}

@router.get("/alunos/{aluno_id}/responsaveis")
async def listar_responsaveis_do_aluno(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os responsáveis vinculados a um aluno específico."""
    return await crud_alunos.listar_responsaveis_do_aluno(db, utilizador["tenant_id"], aluno_id)

# ==========================================
# ACESSO AO PORTAL (login próprio para Aluno/Responsável)
# ==========================================
@router.post("/alunos/{aluno_id}/criar-acesso", status_code=status.HTTP_201_CREATED)
async def criar_acesso_aluno(
    aluno_id: uuid.UUID,
    dados: CriarAcessoRequest,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Concede ao aluno login próprio no Portal (leitura do seu horário/boletim/financeiro)."""
    novo_usuario = await crud_alunos.criar_acesso_aluno(db, utilizador["tenant_id"], aluno_id, dados)
    return {"mensagem": "Acesso ao Portal criado com sucesso.", "usuario_id": novo_usuario.id}

@router.post("/responsaveis/{responsavel_id}/criar-acesso", status_code=status.HTTP_201_CREATED)
async def criar_acesso_responsavel(
    responsavel_id: uuid.UUID,
    dados: CriarAcessoRequest,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Concede ao responsável login próprio no Portal (ver/pagar as faturas dos seus educandos)."""
    novo_usuario = await crud_alunos.criar_acesso_responsavel(db, utilizador["tenant_id"], responsavel_id, dados)
    return {"mensagem": "Acesso ao Portal criado com sucesso.", "usuario_id": novo_usuario.id}

# ==========================================
# DOCUMENTOS DO ALUNO (sobretudo Histórico Escolar de Transferência/Reingresso)
# ==========================================
@router.get("/alunos/{aluno_id}/documentos")
async def listar_documentos_aluno(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    return await crud_alunos.listar_documentos_aluno(db, utilizador["tenant_id"], aluno_id)

@router.post("/alunos/{aluno_id}/documentos", status_code=status.HTTP_201_CREATED)
async def adicionar_documento_aluno(
    aluno_id: uuid.UUID,
    descricao: str | None = None,
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Anexa um documento de apoio ao aluno (ex: Histórico Escolar recebido em papel de outra escola)."""
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    documentos = await crud_alunos.adicionar_documento_aluno(
        db, utilizador["tenant_id"], aluno_id, descricao,
        ficheiro.filename or "documento", ficheiro.content_type or "application/octet-stream", conteudo
    )
    return {"documentos": documentos}

@router.delete("/alunos/{aluno_id}/documentos/{documento_id}")
async def remover_documento_aluno(
    aluno_id: uuid.UUID,
    documento_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    documentos = await crud_alunos.remover_documento_aluno(db, utilizador["tenant_id"], aluno_id, documento_id)
    return {"documentos": documentos}

@router.get("/alunos/{aluno_id}/documentos/{documento_id}/url")
async def obter_documento_aluno(
    aluno_id: uuid.UUID,
    documento_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Devolve o documento como data URI para consulta — pedido só quando aberto."""
    url = await crud_alunos.obter_documento_aluno_url(db, utilizador["tenant_id"], aluno_id, documento_id)
    return {"url": url}

# ==========================================
# FOTO DE PERFIL (a que vale para o cartão de acesso)
# ==========================================
@router.get("/alunos/{aluno_id}/fotos-perfil")
async def listar_fotos_perfil(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    return await crud_alunos.listar_fotos_perfil(db, utilizador["tenant_id"], aluno_id)

@router.post("/alunos/{aluno_id}/foto-perfil", status_code=status.HTTP_201_CREATED)
async def enviar_foto_perfil(
    aluno_id: uuid.UUID,
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Envia uma nova fotografia de perfil (a que vale para o cartão de
    acesso) — arquiva a anterior, nunca a apaga."""
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    fotos = await crud_alunos.enviar_foto_perfil(
        db, utilizador["tenant_id"], aluno_id, utilizador["usuario_id"],
        ficheiro.filename or "foto", ficheiro.content_type or "application/octet-stream", conteudo
    )
    return {"fotos": fotos}

@router.get("/alunos/{aluno_id}/fotos-perfil/{foto_id}/url")
async def obter_foto_perfil(
    aluno_id: uuid.UUID,
    foto_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Devolve a fotografia como data URI — pedida só quando aberta."""
    url = await crud_alunos.obter_foto_perfil_url(db, utilizador["tenant_id"], aluno_id, foto_id)
    return {"url": url}
