"""
Acesso a dados do Painel de Indicadores (BI) — agrega dados já
produzidos por outros módulos (Académico, Matrículas, Financeiro,
Diário, CRM) numa visão executiva para o Gestor/Secretaria.

Não introduz nenhuma tabela nova nem regra de negócio própria: a única
lógica reaproveitada de outro módulo é o cálculo de juros/multa
(calcular_situacao_fatura, de cruds/financeiro.py), para não duplicar
essa RN aqui — todo o resto é apenas agregação (COUNT/AVG/SUM).
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_matricula import Matricula
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade
from app.database.models_diario import Avaliacao, NotaAvaliacao, RegistroNota
from app.database.models_crm import FunilEtapa, LeadCandidato, OportunidadeCRM
from app.cruds import financeiro as crud_financeiro


# ==========================================
# A. ACADÉMICO — ALUNOS ATIVOS E OCUPAÇÃO DE VAGAS
# ==========================================
async def obter_resumo_academico(db: AsyncSession, tenant_id) -> dict:
    total_alunos_ativos = (await db.execute(
        select(func.count(func.distinct(Matricula.aluno_id))).where(
            Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO"
        )
    )).scalar_one()

    linhas = (await db.execute(
        select(Turma.id, Turma.nome_codigo, Turma.vagas_maximas, func.count(Matricula.id))
        .outerjoin(Matricula, (Matricula.turma_id == Turma.id) & (Matricula.status_matricula == "ATIVO"))
        .where(Turma.tenant_id == tenant_id)
        .group_by(Turma.id, Turma.nome_codigo, Turma.vagas_maximas)
        .order_by(Turma.nome_codigo)
    )).all()

    ocupacao_por_turma = [
        {
            "turma_id": turma_id,
            "nome_turma": nome_turma,
            "vagas_maximas": vagas_maximas,
            "matriculados": matriculados,
            "taxa_ocupacao": round(matriculados / vagas_maximas * 100, 1) if vagas_maximas else 0.0,
        }
        for turma_id, nome_turma, vagas_maximas, matriculados in linhas
    ]

    total_vagas = sum(t["vagas_maximas"] for t in ocupacao_por_turma)
    total_matriculados = sum(t["matriculados"] for t in ocupacao_por_turma)

    return {
        "total_alunos_ativos": total_alunos_ativos,
        "total_vagas": total_vagas,
        "taxa_ocupacao_geral": round(total_matriculados / total_vagas * 100, 1) if total_vagas else 0.0,
        "ocupacao_por_turma": ocupacao_por_turma,
    }


# ==========================================
# B. DESEMPENHO MÉDIO POR TURMA (todas as disciplinas)
# ==========================================
async def obter_desempenho_por_turma(db: AsyncSession, tenant_id) -> list[dict]:
    resultado = await db.execute(
        select(
            Turma.id, Turma.nome_codigo,
            func.avg(RegistroNota.valor_nota), func.count(func.distinct(RegistroNota.matricula_id))
        )
        .join(Matricula, Matricula.turma_id == Turma.id)
        .join(RegistroNota, RegistroNota.matricula_id == Matricula.id)
        .where(Turma.tenant_id == tenant_id)
        .group_by(Turma.id, Turma.nome_codigo)
        .order_by(Turma.nome_codigo)
    )
    return [
        {
            "turma_id": turma_id,
            "nome_turma": nome_turma,
            "media": round(float(media), 2) if media is not None else None,
            "total_alunos_avaliados": total_alunos,
        }
        for turma_id, nome_turma, media, total_alunos in resultado.all()
    ]


# ==========================================
# C. FINANCEIRO — INADIMPLÊNCIA E RECEITA
# ==========================================
async def obter_resumo_financeiro(db: AsyncSession, tenant_id) -> dict:
    faturas_em_aberto = (await db.execute(
        select(FaturaMensalidade).where(
            FaturaMensalidade.tenant_id == tenant_id, FaturaMensalidade.status_pagamento == "PENDENTE"
        )
    )).scalars().all()

    total_atrasadas = 0
    valor_total_atraso = Decimal("0.00")
    for fatura in faturas_em_aberto:
        situacao = crud_financeiro.calcular_situacao_fatura(fatura)
        if situacao["status_efetivo"] == "ATRASADO":
            total_atrasadas += 1
            valor_total_atraso += situacao["valor_atualizado"]

    total_em_aberto = len(faturas_em_aberto)
    taxa_inadimplencia = round(total_atrasadas / total_em_aberto * 100, 1) if total_em_aberto else 0.0

    hoje = date.today()
    receita_mes = (await db.execute(
        select(func.coalesce(func.sum(FaturaMensalidade.valor_pago_realizado), 0)).where(
            FaturaMensalidade.tenant_id == tenant_id,
            FaturaMensalidade.status_pagamento == "PAGO",
            func.extract("year", FaturaMensalidade.data_pagamento_realizado) == hoje.year,
            func.extract("month", FaturaMensalidade.data_pagamento_realizado) == hoje.month,
        )
    )).scalar_one()

    total_contratos = (await db.execute(
        select(func.count(ContratoFinanceiro.id)).where(ContratoFinanceiro.tenant_id == tenant_id)
    )).scalar_one()

    return {
        "total_faturas_em_aberto": total_em_aberto,
        "total_faturas_atrasadas": total_atrasadas,
        "taxa_inadimplencia": taxa_inadimplencia,
        "valor_total_em_atraso": valor_total_atraso,
        "receita_recebida_mes_atual": receita_mes,
        "total_contratos_ativos": total_contratos,
    }


# ==========================================
# D. CRM — FUNIL E TAXA DE CONVERSÃO
# ==========================================
async def obter_funil_crm(db: AsyncSession, tenant_id) -> dict:
    etapas = (await db.execute(
        select(FunilEtapa).where(FunilEtapa.tenant_id == tenant_id).order_by(FunilEtapa.ordem)
    )).scalars().all()

    contagem_por_etapa = dict((await db.execute(
        select(OportunidadeCRM.etapa_id, func.count(OportunidadeCRM.id))
        .where(OportunidadeCRM.tenant_id == tenant_id)
        .group_by(OportunidadeCRM.etapa_id)
    )).all())

    funil = [
        {
            "etapa_id": etapa.id,
            "nome_etapa": etapa.nome_etapa,
            "eh_etapa_ganho": etapa.eh_etapa_ganho,
            "total": contagem_por_etapa.get(etapa.id, 0),
        }
        for etapa in etapas
    ]

    total_leads = (await db.execute(
        select(func.count(LeadCandidato.id)).where(LeadCandidato.tenant_id == tenant_id)
    )).scalar_one()
    total_convertidos = sum(item["total"] for item in funil if item["eh_etapa_ganho"])
    taxa_conversao = round(total_convertidos / total_leads * 100, 1) if total_leads else 0.0

    return {
        "funil": funil,
        "total_leads": total_leads,
        "total_convertidos": total_convertidos,
        "taxa_conversao": taxa_conversao,
    }


# ==========================================
# E. EFICIÊNCIA POR OBJETIVO DE APRENDIZAGEM
# ==========================================
async def obter_eficiencia_por_objetivo(db: AsyncSession, tenant_id) -> list[dict]:
    """
    Para cada objetivo de aprendizagem (ex.: "Células" em Ciências) com
    pelo menos uma nota lançada numa Avaliacao marcada com ele, a média
    dessas notas comparada com a média geral da disciplina (todas as
    avaliações da disciplina, com ou sem objetivo associado) — é isto
    que responde "os alunos aprenderam bem X?" em vez de só "qual a
    média a Ciências?". Avaliações sem objetivo associado não entram
    aqui (só contam para a média geral da disciplina).
    """
    linhas_objetivo = (await db.execute(
        select(
            Disciplina.id, Disciplina.nome,
            ObjetivoAprendizagem.id, ObjetivoAprendizagem.nome,
            func.avg(NotaAvaliacao.valor_nota), func.count(NotaAvaliacao.id)
        )
        .select_from(NotaAvaliacao)
        .join(Avaliacao, Avaliacao.id == NotaAvaliacao.avaliacao_id)
        .join(ObjetivoAprendizagem, ObjetivoAprendizagem.id == Avaliacao.objetivo_aprendizagem_id)
        .join(Disciplina, Disciplina.id == Avaliacao.disciplina_id)
        .where(Avaliacao.tenant_id == tenant_id)
        .group_by(Disciplina.id, Disciplina.nome, ObjetivoAprendizagem.id, ObjetivoAprendizagem.nome)
        .order_by(Disciplina.nome, ObjetivoAprendizagem.nome)
    )).all()

    medias_disciplina = dict((await db.execute(
        select(Avaliacao.disciplina_id, func.avg(NotaAvaliacao.valor_nota))
        .select_from(NotaAvaliacao)
        .join(Avaliacao, Avaliacao.id == NotaAvaliacao.avaliacao_id)
        .where(Avaliacao.tenant_id == tenant_id)
        .group_by(Avaliacao.disciplina_id)
    )).all())

    resultado = []
    for disciplina_id, nome_disciplina, objetivo_id, nome_objetivo, media_objetivo, total_notas in linhas_objetivo:
        media_disciplina = medias_disciplina.get(disciplina_id)
        media_objetivo_f = round(float(media_objetivo), 2)
        media_disciplina_f = round(float(media_disciplina), 2) if media_disciplina is not None else None
        resultado.append({
            "disciplina_id": disciplina_id,
            "nome_disciplina": nome_disciplina,
            "objetivo_id": objetivo_id,
            "nome_objetivo": nome_objetivo,
            "media_objetivo": media_objetivo_f,
            "media_disciplina": media_disciplina_f,
            "total_notas": total_notas,
            "abaixo_da_media": media_disciplina_f is not None and media_objetivo_f < media_disciplina_f,
        })
    return resultado


# ==========================================
# F. AGREGADO GERAL DO PAINEL
# ==========================================
async def obter_indicadores(db: AsyncSession, tenant_id) -> dict:
    return {
        "academico": await obter_resumo_academico(db, tenant_id),
        "desempenho_por_turma": await obter_desempenho_por_turma(db, tenant_id),
        "eficiencia_por_objetivo": await obter_eficiencia_por_objetivo(db, tenant_id),
        "financeiro": await obter_resumo_financeiro(db, tenant_id),
        "crm": await obter_funil_crm(db, tenant_id),
    }
