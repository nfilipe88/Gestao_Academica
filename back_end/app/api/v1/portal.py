import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import portal as crud_portal

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
