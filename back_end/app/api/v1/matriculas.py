from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.schemas.matriculas import MatriculaCreate, MatriculaStatusUpdate
from app.cruds import matriculas as crud_matriculas

router = APIRouter(prefix="/api/v1", tags=["Matrículas"])

# Quem pode matricular/alterar status (RBAC) — leitura fica aberta a
# qualquer utilizador autenticado da escola.
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# A. CRIAR NOVA MATRÍCULA
# ==========================================
@router.post("/matriculas", status_code=status.HTTP_201_CREATED)
async def criar_matricula(
    dados: MatriculaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Efetua a matrícula de um aluno numa turma, aplicando as regras de negócio RN01-RN05."""
    return await crud_matriculas.criar_matricula(db, utilizador["tenant_id"], dados)

# ==========================================
# B. LISTAR MATRÍCULAS DE UMA TURMA (Diário de Classe)
# ==========================================
@router.get("/turmas/{turma_id}/matriculas")
async def listar_matriculas_da_turma(
    turma_id: uuid.UUID,
    status_matricula: str | None = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os alunos matriculados numa turma. ?status_matricula=ATIVO filtra só os ativos."""
    return await crud_matriculas.listar_matriculas_da_turma(db, utilizador["tenant_id"], turma_id, status_matricula)

# ==========================================
# C. ALTERAR STATUS DA MATRÍCULA
# ==========================================
@router.patch("/matriculas/{matricula_id}/status")
async def atualizar_status_matricula(
    matricula_id: uuid.UUID,
    dados: MatriculaStatusUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Atualiza a situação do aluno (ex: de Ativo para Trancado, Transferido ou Evadido)."""
    await crud_matriculas.atualizar_status_matricula(db, utilizador["tenant_id"], matricula_id, dados)
    return {"mensagem": "Status da matrícula atualizado com sucesso."}

# ==========================================
# D. CONSULTAR HISTÓRICO DO ALUNO
# ==========================================
@router.get("/alunos/{aluno_id}/matriculas")
async def listar_matriculas_do_aluno(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Mostra todas as turmas e anos letivos pelos quais o aluno já passou na escola."""
    return await crud_matriculas.listar_matriculas_do_aluno(db, utilizador["tenant_id"], aluno_id)
