import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import resultados as motor
from app.core.security import exigir_perfil
from app.cruds.matriculas import _ano_letivo_corrente
from app.database.models import Tenant
from app.database.models_diario import PeriodoAvaliacao
from app.database.models_matricula import Matricula
from app.database.session import obter_sessao_db

router = APIRouter(prefix="/api/v1/fecho", tags=["Fecho do Trimestre e do Ano"])
logger = logging.getLogger("fecho")

_PODE_VER = exigir_perfil("GESTOR", "SECRETARIA")
_PODE_FECHAR = exigir_perfil("GESTOR")


async def _tenant(db: AsyncSession, tenant_id) -> Tenant:
    return (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()


@router.get("/periodos/{periodo_id}/pendencias")
async def pendencias_do_periodo(
    periodo_id: uuid.UUID, ano_letivo: int | None = Query(default=None),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_VER),
):
    """Antes de trancar um trimestre: que turmas/disciplinas ainda têm alunos sem nota, e de que professor."""
    tenant_id = utilizador["tenant_id"]
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.id == periodo_id, PeriodoAvaliacao.tenant_id == tenant_id)
    )).scalars().first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período de avaliação não encontrado na sua instituição.")
    ano = ano_letivo if ano_letivo is not None else await _ano_letivo_corrente(db, tenant_id)
    pendencias = await motor.pendencias_do_periodo(db, tenant_id, periodo.nome, ano) if ano is not None else []
    return {"periodo": periodo.nome, "ano_letivo": ano, "aberto": periodo.aberto, "pendencias": pendencias,
            "total_alunos_sem_nota": sum(p["sem_nota"] for p in pendencias)}


@router.get("/ano/{ano_letivo}/previa")
async def previa_do_fecho_do_ano(
    ano_letivo: int, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_VER),
):
    """O que aconteceria se o ano fosse fechado agora — não grava nada."""
    tenant = await _tenant(db, utilizador["tenant_id"])
    resultados = await motor.calcular_resultados_do_ano(db, tenant, ano_letivo)
    periodos_abertos = [p.nome for p in await motor.periodos_registados(db, tenant.id) if p.aberto]
    return {
        "ano_letivo": ano_letivo,
        "nota_minima_aprovacao": float(tenant.nota_minima_aprovacao) if tenant.nota_minima_aprovacao is not None else None,
        "max_disciplinas_reprovadas": tenant.max_disciplinas_reprovadas,
        "limite_faltas_percentagem": float(tenant.limite_faltas_percentagem) if tenant.limite_faltas_percentagem is not None else None,
        "periodos_abertos": periodos_abertos,
        "pode_fechar": tenant.nota_minima_aprovacao is not None and not periodos_abertos,
        "resumo": motor.resumir(resultados),
        "ja_fechados": sum(1 for r in resultados if r["resultado_atual"]),
        "alunos": resultados,
    }


@router.post("/ano/{ano_letivo}")
async def fechar_ano_letivo(
    ano_letivo: int, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_FECHAR),
):
    """Grava o resultado final (APROVADO/REPROVADO/REPROVADO_FALTAS) nas matrículas ATIVO do ano.
    Exige nota mínima definida e todos os períodos trancados. Alunos com notas em falta
    ficam por fechar e são devolvidos na resposta; pode voltar a correr depois de os corrigir."""
    tenant = await _tenant(db, utilizador["tenant_id"])
    if tenant.nota_minima_aprovacao is None:
        raise HTTPException(status_code=400, detail="Defina a nota mínima de aprovação em Configurações antes de fechar o ano.")
    abertos = [p.nome for p in await motor.periodos_registados(db, tenant.id) if p.aberto]
    if abertos:
        raise HTTPException(status_code=400, detail=f"Tranque primeiro os períodos de avaliação: {', '.join(abertos)}.")

    resultados = await motor.calcular_resultados_do_ano(db, tenant, ano_letivo)
    if not resultados:
        raise HTTPException(status_code=404, detail="Não há matrículas ativas neste ano letivo.")

    agora = datetime.now(timezone.utc)
    por_id = {r["matricula_id"]: r for r in resultados}
    matriculas = (await db.execute(select(Matricula).where(Matricula.id.in_(list(por_id))))).scalars().all()
    fechados = 0
    for matricula in matriculas:
        r = por_id[matricula.id]
        if r["resultado"] == "INCOMPLETO" or matricula.resultado_final:
            continue
        matricula.resultado_final = r["resultado"]
        matricula.resultado_em = agora
        matricula.resultado_detalhe = {
            "disciplinas": r["disciplinas"], "faltas": r["faltas"], "aulas": r["aulas"], "faltas_percentagem": r["faltas_percentagem"],
            "criterios": {"nota_minima": float(tenant.nota_minima_aprovacao), "max_disciplinas_reprovadas": tenant.max_disciplinas_reprovadas,
                          "limite_faltas_percentagem": float(tenant.limite_faltas_percentagem) if tenant.limite_faltas_percentagem is not None else None},
        }
        fechados += 1
    await db.commit()
    logger.info("Fecho do ano %s: tenant=%s por=%s fechados=%s", ano_letivo, tenant.id, utilizador.get("usuario_id"), fechados)

    incompletos = [{"aluno": r["nome_completo"], "turma": r["turma"], "disciplinas_em_falta": r["em_falta"]}
                   for r in resultados if r["resultado"] == "INCOMPLETO" and not r["resultado_atual"]]
    return {"ano_letivo": ano_letivo, "fechados": fechados, "incompletos": incompletos,
            "completo": not incompletos, "resumo": motor.resumir(resultados)}


@router.post("/ano/{ano_letivo}/reabrir")
async def reabrir_ano_letivo(
    ano_letivo: int, db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_FECHAR),
):
    """Anula os resultados finais do ano (para corrigir notas e fechar de novo)."""
    matriculas = (await db.execute(
        select(Matricula).where(Matricula.tenant_id == utilizador["tenant_id"], Matricula.ano_letivo == ano_letivo,
                                Matricula.resultado_final.is_not(None))
    )).scalars().all()
    for m in matriculas:
        m.resultado_final = m.resultado_detalhe = m.resultado_em = None
    await db.commit()
    logger.info("Reabertura do ano %s: tenant=%s por=%s matriculas=%s", ano_letivo, utilizador["tenant_id"], utilizador.get("usuario_id"), len(matriculas))
    return {"ano_letivo": ano_letivo, "reabertas": len(matriculas)}
