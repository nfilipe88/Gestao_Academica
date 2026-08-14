import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.schemas.horarios import HorarioAulaCreate, HorarioAulaUpdate
from app.cruds import horarios as crud_horarios

router = APIRouter(prefix="/api/v1/horarios", tags=["Horários"])

# Só Gestor/Secretaria montam a grade horária — leitura fica aberta a
# qualquer funcionário da escola (GESTOR/SECRETARIA/PROFESSOR, Professor
# precisa de ver a sua). ALUNO/RESPONSAVEL usam antes o Portal
# (app/api/v1/portal.py), que já filtra pelos seus próprios educandos.
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# CONSULTA DA GRADE
# ==========================================
@router.get("/turmas/{turma_id}")
async def listar_grade_da_turma(
    turma_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Grade horária semanal de uma turma."""
    return await crud_horarios.listar_grade_da_turma(db, utilizador["tenant_id"], turma_id)

@router.get("/professores/{professor_id}")
async def listar_grade_do_professor(
    professor_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Grade horária semanal de um professor (uso administrativo)."""
    return await crud_horarios.listar_grade_do_professor(db, utilizador["tenant_id"], professor_id)

@router.get("/minha-grade")
async def listar_minha_grade(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Grade horária semanal do professor autenticado."""
    return await crud_horarios.listar_minha_grade(db, utilizador)

# ==========================================
# GESTÃO DA GRADE (Gestor/Secretaria)
# ==========================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_horario(
    dados: HorarioAulaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Adiciona um slot à grade horária (RN01/RN02 — sem sobreposição de turma nem de professor)."""
    return await crud_horarios.criar_horario(db, utilizador["tenant_id"], dados)

@router.patch("/{horario_id}")
async def atualizar_horario(
    horario_id: uuid.UUID,
    dados: HorarioAulaUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Move/edita um slot já existente, revalidando conflitos."""
    return await crud_horarios.atualizar_horario(db, utilizador["tenant_id"], horario_id, dados)

@router.delete("/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_horario(
    horario_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Remove um slot da grade horária."""
    await crud_horarios.remover_horario(db, utilizador["tenant_id"], horario_id)
