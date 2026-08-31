from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.core import estatisticas_excel
from app.cruds import estatisticas as crud_estatisticas

router = APIRouter(prefix="/api/v1/estatisticas", tags=["Estatísticas"])

# Mesma visão executiva do Indicadores — só quem gere a instituição em si.
_PODE_ACEDER = exigir_perfil("GESTOR", "SECRETARIA")


@router.get("/dashboard")
async def obter_dashboard(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Estado corrente da escola (sem filtro de datas): alunos matriculados
    por faixa etária, cursos mais concorridos, disciplinas/turmas/alunos
    com melhores notas, resumo financeiro."""
    return await crud_estatisticas.obter_dashboard(db, utilizador["tenant_id"])


@router.get("/relatorio")
async def obter_relatorio(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """O mesmo relatório do Dashboard, filtrado por intervalo de datas —
    inclui também as estatísticas financeiras (pagamentos/despesas por
    mês, atrasos, maiores entradas/saídas do período). Base dos exports
    .xlsx/.xls abaixo."""
    return await crud_estatisticas.obter_relatorio(db, utilizador["tenant_id"], data_inicio, data_fim)


@router.get("/relatorio.xlsx")
async def exportar_relatorio_xlsx(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    relatorio = await crud_estatisticas.obter_relatorio(db, utilizador["tenant_id"], data_inicio, data_fim)
    conteudo = estatisticas_excel.gerar_xlsx(relatorio)
    return Response(
        content=conteudo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="estatisticas-{data_inicio}-a-{data_fim}.xlsx"'}
    )


@router.get("/relatorio.xls")
async def exportar_relatorio_xls(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Formato binário pré-2007 — mantido só para quem precise mesmo dele; .xlsx acima é o formato recomendado."""
    relatorio = await crud_estatisticas.obter_relatorio(db, utilizador["tenant_id"], data_inicio, data_fim)
    conteudo = estatisticas_excel.gerar_xls(relatorio)
    return Response(
        content=conteudo, media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f'attachment; filename="estatisticas-{data_inicio}-a-{data_fim}.xls"'}
    )
