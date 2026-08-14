from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.core.email import enviar_email, template_base
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
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os alunos da escola do utilizador logado."""
    return await crud_alunos.listar_alunos(db, utilizador["tenant_id"])

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
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os responsáveis da escola do utilizador logado."""
    return await crud_alunos.listar_responsaveis(db, utilizador["tenant_id"])

# ==========================================
# VÍNCULO ALUNO <-> RESPONSÁVEL
# ==========================================
@router.post("/alunos/{aluno_id}/responsaveis", status_code=status.HTTP_201_CREATED)
async def vincular_responsavel(
    aluno_id: uuid.UUID,
    dados: VincularResponsavel,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Vincula um responsável já existente a um aluno (RN: um aluno pode ter vários responsáveis)."""
    vinculo, aluno, responsavel = await crud_alunos.vincular_responsavel(db, utilizador["tenant_id"], aluno_id, dados)

    # E-mail de notificação (best-effort, em background). Só envia se o
    # responsável tiver um e-mail registado — é opcional no cadastro.
    if responsavel.email:
        background_tasks.add_task(
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
