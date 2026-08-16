from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.core.email import enviar_email, template_base
from app.schemas.professores import AlocacaoCreate, ProfessorCreate
from app.cruds import professores as crud_professores

router = APIRouter(prefix="/api/v1/professores", tags=["Professores"])

# Quem pode alocar professores a turmas/disciplinas (RBAC).
_PODE_ALOCAR = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# ROTAS
# ==========================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_professor(
    dados: ProfessorCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    # Só o Gestor pode criar contas de Professor (RBAC).
    utilizador: dict = Depends(exigir_perfil("GESTOR"))
):
    """Cria a conta de Professor (Usuario + Professor, numa única transação)."""
    novo_professor, novo_usuario = await crud_professores.criar_professor(db, utilizador["tenant_id"], dados)

    background_tasks.add_task(
        enviar_email,
        destinatario=dados.email,
        assunto="A sua conta de Professor foi criada",
        corpo_html=template_base(
            "Bem-vindo(a) à equipa docente!",
            f"""
            <p>Olá {dados.nome_completo},</p>
            <p>Foi criada uma conta de Professor para si na plataforma de Gestão Académica.</p>
            <p>Já pode iniciar sessão com o e-mail <strong>{dados.email}</strong> e a
            palavra-passe definida no momento do registo.</p>
            """
        )
    )

    return {
        "id": novo_professor.id,
        "usuario_id": novo_usuario.id,
        "nome_completo": dados.nome_completo,
        "email": dados.email,
        "formacao_academica": dados.formacao_academica,
        "data_criacao": novo_professor.data_criacao,
    }

@router.get("")
async def listar_professores(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    busca: str | None = Query(None, description="Filtra por nome ou e-mail (parcial)."),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os professores da escola do utilizador logado, paginados e opcionalmente filtrados."""
    return await crud_professores.listar_professores(db, utilizador["tenant_id"], page, page_size, busca)

# ==========================================
# ALOCAÇÃO (Professor <-> Turma <-> Disciplina)
# ==========================================
@router.post("/{professor_id}/alocacoes", status_code=status.HTTP_201_CREATED)
async def alocar_professor(
    professor_id: uuid.UUID,
    dados: AlocacaoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ALOCAR)
):
    """Define que este professor lecciona esta disciplina nesta turma."""
    alocacao = await crud_professores.alocar_professor(db, utilizador["tenant_id"], professor_id, dados)
    return {"mensagem": "Professor alocado com sucesso", "id": alocacao.id}

@router.get("/alocacoes/minhas")
async def listar_minhas_alocacoes(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """
    Lista as alocações (turma+disciplina) do professor autenticado — usadas
    pelo Diário de Classe para saber a que turmas/disciplinas ele tem acesso.
    Gestor/Secretaria recebem todas as alocações da escola.
    """
    return await crud_professores.listar_minhas_alocacoes(db, utilizador)
