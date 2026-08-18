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
