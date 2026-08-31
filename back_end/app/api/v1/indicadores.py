import uuid

from fastapi import APIRouter, Depends, Response
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


@router.get("/relatorio.pdf")
async def obter_relatorio_pdf(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Fotografia completa do painel em PDF, pronta a imprimir/arquivar."""
    pdf_bytes = await crud_indicadores.gerar_pdf_relatorio(db, utilizador["tenant_id"])
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="relatorio-indicadores.pdf"'}
    )


@router.get("/risco-evasao/exportar.csv")
async def exportar_risco_evasao_csv(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """CSV da lista de Risco de Evasão, uma linha por aluno — para levar
    para Excel/Google Sheets."""
    csv_texto = await crud_indicadores.gerar_csv_risco_evasao(db, utilizador["tenant_id"])
    return Response(
        content=csv_texto.encode("utf-8"), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="risco-evasao.csv"'}
    )


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
