from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.schemas.comportamento import RegistroComportamentoCreate
from app.cruds import comportamento as crud_comportamento

router = APIRouter(prefix="/api/v1/comportamento", tags=["Comportamento"])

# Leitura e registo: Gestor/Secretaria sempre; Professor só nas turmas
# onde lecciona (validado dentro do crud) — mesmo alcance do Diário de
# Classe, ver app/cruds/diario.py.
_PODE_ACEDER = exigir_perfil("GESTOR", "SECRETARIA", "PROFESSOR")


@router.post("/turmas/{turma_id}/alunos/{aluno_id}", status_code=status.HTTP_201_CREATED)
async def registar_comportamento(
    turma_id: uuid.UUID,
    aluno_id: uuid.UUID,
    dados: RegistroComportamentoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Regista um incidente/observação de comportamento (positivo ou negativo) de um aluno."""
    return await crud_comportamento.registar_comportamento(db, utilizador, turma_id, aluno_id, dados)


@router.get("/turmas/{turma_id}/alunos/{aluno_id}")
async def listar_comportamento(
    turma_id: uuid.UUID,
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Histórico de comportamento do aluno nesta turma, mais recente primeiro."""
    return await crud_comportamento.listar_comportamento_da_turma_aluno(db, utilizador, turma_id, aluno_id)


@router.delete("/registos/{registo_id}")
async def remover_comportamento(
    registo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    await crud_comportamento.remover_comportamento(db, utilizador, registo_id)
    return {"mensagem": "Registo removido com sucesso."}
