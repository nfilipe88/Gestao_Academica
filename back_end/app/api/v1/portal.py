import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import portal as crud_portal
from app.schemas.lms import ProfVirtualPerguntaCreate

router = APIRouter(prefix="/api/v1/portal", tags=["Portal do Aluno/Responsável"])

# Só logins ALUNO/RESPONSAVEL usam este router — Gestor/Secretaria/
# Professor já têm as suas próprias telas (Matrículas, Diário,
# Horários, Financeiro) com visão completa da escola.
_PODE_ACEDER = exigir_perfil("ALUNO", "RESPONSAVEL")


@router.get("/meus-educandos")
async def listar_meus_educandos(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Alunos que este login pode consultar — o próprio (ALUNO) ou os seus educandos (RESPONSAVEL)."""
    return await crud_portal.listar_meus_educandos(db, utilizador["tenant_id"], utilizador)


@router.get("/educandos/{aluno_id}/horario")
async def obter_horario_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Grade horária semanal da turma atual do educando."""
    return await crud_portal.obter_horario_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/boletim")
async def obter_boletim_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Notas e frequência do educando, agrupadas por disciplina."""
    return await crud_portal.obter_boletim_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/financeiro")
async def obter_financeiro_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """
    Contrato e extrato de faturas do educando. Para pagar, o front-end
    chama diretamente POST /financeiro/faturas/{id}/gerar-cobranca e
    /financeiro/transacoes/capturar — já abertos a qualquer autenticado
    e com o mesmo controlo de posse aplicado aqui (ver cruds/financeiro.py).
    """
    return await crud_portal.obter_financeiro_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/tarefas")
async def listar_tarefas_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Trabalhos/tarefas do educando (prazo, status de entrega e nota, quando já avaliado)."""
    return await crud_portal.listar_tarefas_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/materiais")
async def listar_materiais_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Materiais de aula publicados para a turma atual do educando."""
    return await crud_portal.listar_materiais_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/materiais/{material_id}")
async def obter_material_do_educando(
    aluno_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Conteúdo de um material de aula — só se pertencer à turma atual do educando."""
    return await crud_portal.obter_material_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, material_id)


@router.post("/educandos/{aluno_id}/prof-virtual")
async def perguntar_prof_virtual(
    aluno_id: uuid.UUID,
    dados: ProfVirtualPerguntaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Envia uma pergunta ao Prof. Virtual sobre um material de aula concreto. Devolve a resposta (chat sem persistência — o histórico viaja no pedido)."""
    resposta = await crud_portal.perguntar_prof_virtual_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, dados)
    return {"resposta": resposta}
