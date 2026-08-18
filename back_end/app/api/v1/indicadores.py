import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import indicadores as crud_indicadores

router = APIRouter(prefix="/api/v1/indicadores", tags=["Indicadores"])

# Visão executiva da escola — só quem gere a instituição em si.
_PODE_ACEDER = exigir_perfil("GESTOR", "SECRETARIA")


@router.get("")
async def obter_indicadores(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Painel de indicadores (BI): ocupação de vagas, desempenho por turma, inadimplência/receita, funil do CRM e resumo de risco de evasão."""
    return await crud_indicadores.obter_indicadores(db, utilizador["tenant_id"])


@router.get("/risco-evasao")
async def obter_risco_evasao(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Lista de alunos com sinais de risco de evasão (faltas, queda de notas, mensalidades em atraso), pontuados por regras e ordenados do mais para o menos arriscado."""
    return await crud_indicadores.obter_risco_evasao(db, utilizador["tenant_id"])


@router.post("/risco-evasao/{matricula_id}/trilha-recuperacao")
async def gerar_trilha_recuperacao(
    matricula_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Pede ao Prof. Virtual (IA) um plano de recuperação para este aluno, a partir do seu perfil de risco atual. Fica gravado no histórico."""
    return await crud_indicadores.gerar_trilha_recuperacao(db, utilizador["tenant_id"], matricula_id, utilizador["usuario_id"])


@router.get("/risco-evasao/{matricula_id}/trilhas")
async def listar_trilhas_do_aluno(
    matricula_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Histórico de trilhas de recuperação já geradas para este aluno, mais recente primeiro."""
    return await crud_indicadores.listar_trilhas_do_aluno(db, utilizador["tenant_id"], matricula_id)
