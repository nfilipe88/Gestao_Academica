import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil_staff
from app.schemas.tarefas import AvaliarTarefaLote, TarefaCreate
from app.cruds import tarefas as crud_tarefas

router = APIRouter(prefix="/api/v1/tarefas", tags=["Trabalhos/Tarefas"])

# Leitura/gestão aberta a qualquer funcionário da escola — a RN01 de
# autoria (Professor só na sua própria alocação) vive no crud.
# ALUNO/RESPONSAVEL usam antes o Portal (GET /portal/educandos/{id}/tarefas).


@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_tarefa(
    dados: TarefaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Cria um trabalho/tarefa para uma turma+disciplina (via a alocação do professor)."""
    return await crud_tarefas.criar_tarefa(db, utilizador, dados)


@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}")
async def listar_tarefas_da_turma_disciplina(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os trabalhos/tarefas já atribuídos a esta turma+disciplina."""
    return await crud_tarefas.listar_tarefas_da_turma_disciplina(db, utilizador, turma_id, disciplina_id)


@router.get("/{tarefa_id}")
async def obter_tarefa(
    tarefa_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Detalhe do trabalho/tarefa com a lista de avaliações por aluno — usado na tela de correção."""
    return await crud_tarefas.obter_tarefa_com_avaliacoes(db, utilizador, tarefa_id)


@router.post("/{tarefa_id}/avaliar")
async def avaliar_tarefa(
    tarefa_id: uuid.UUID,
    dados: AvaliarTarefaLote,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Regista em lote o status de entrega e a nota de cada aluno para este trabalho/tarefa."""
    total = await crud_tarefas.avaliar_tarefa_lote(db, utilizador, tarefa_id, dados)
    return {"mensagem": f"Avaliação registada para {total} aluno(s)."}
