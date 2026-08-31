"""
Acesso a dados do Painel de Indicadores (BI) — agrega dados já
produzidos por outros módulos (Académico, Matrículas, Financeiro,
Diário, CRM) numa visão executiva para o Gestor/Secretaria.

Não introduz nenhuma tabela nova nem regra de negócio própria: a única
lógica reaproveitada de outro módulo é o cálculo de juros/multa
(calcular_situacao_fatura, de cruds/financeiro.py), para não duplicar
essa RN aqui — todo o resto é apenas agregação (COUNT/AVG/SUM).
"""
import csv
import io
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.database.models import Tenant
from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade
from app.database.models_diario import Avaliacao, NotaAvaliacao, RegistroFrequencia, RegistroNota
from app.database.models_crm import FunilEtapa, LeadCandidato, OportunidadeCRM
from app.database.models_bi import TrilhaRecuperacao
from app.cruds import financeiro as crud_financeiro
from app.core import documentos_pdf, prof_virtual, storage


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
# G. RISCO DE EVASÃO — pontuação por regras (não é Machine Learning)
# ==========================================
# Pesos fixos e explicáveis por sinal, somados num score 0-100 —
# calculado on-demand a cada pedido (nunca persistido: não há
# histórico de score a manter em dia nem risco de ficar desatualizado).
# Isto substitui um modelo estatístico/ML por algo que o Gestor
# consegue auditar linha a linha (ver "fatores" no retorno).
PONTOS_FALTA_ALTA = 40      # taxa de faltas >= 25%
PONTOS_FALTA_MEDIA = 20     # taxa de faltas >= 15%
LIMIAR_FALTA_ALTA = 0.25
LIMIAR_FALTA_MEDIA = 0.15

PONTOS_QUEDA_NOTAS = 25
# Queda relativa (não absoluta) entre a 1ª e a 2ª metade cronológica das
# notas lançadas — cada escola usa a sua própria escala (0-10, 0-20...),
# por isso comparar por percentagem evita depender dessa escala.
LIMIAR_QUEDA_NOTAS = 0.85  # 2ª metade <= 85% da 1ª metade → queda de 15%+

PONTOS_ATRASO_GRAVE = 35    # 2+ mensalidades vencidas por pagar
PONTOS_ATRASO_LEVE = 15     # 1 mensalidade vencida por pagar

LIMIAR_RISCO_ALTO = 50
LIMIAR_RISCO_MEDIO = 25


async def obter_risco_evasao(db: AsyncSession, tenant_id) -> list[dict]:
    """
    Para cada aluno com Matrícula ATIVO, cruza três sinais já existentes
    nos módulos Diário e Financeiro — frequência, tendência de notas e
    mensalidades em atraso — numa pontuação de risco de evasão. Só
    devolve quem tem pelo menos 1 ponto (algum sinal de risco), ordenado
    do mais arriscado para o menos, para o Gestor poder agir sobre a
    lista sem ter de a filtrar primeiro.
    """
    matriculas = (await db.execute(
        select(Matricula.id, Matricula.aluno_id, Aluno.nome_completo, Turma.nome_codigo)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .join(Turma, Turma.id == Matricula.turma_id)
        .where(Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO")
    )).all()
    if not matriculas:
        return []
    matricula_ids = [linha.id for linha in matriculas]

    # --- Sinal 1: frequência ---
    freq_por_matricula = {
        matricula_id: (int(soma_faltas or 0), int(soma_aulas or 0))
        for matricula_id, soma_faltas, soma_aulas in (await db.execute(
            select(
                RegistroFrequencia.matricula_id,
                func.sum(RegistroFrequencia.faltas),
                func.sum(RegistroFrequencia.quantidade_aulas)
            )
            .where(RegistroFrequencia.matricula_id.in_(matricula_ids))
            .group_by(RegistroFrequencia.matricula_id)
        )).all()
    }

    # --- Sinal 2: tendência de notas (ordenadas cronologicamente para dividir em 2 metades) ---
    notas_por_matricula: dict = {}
    for matricula_id, valor_nota in (await db.execute(
        select(RegistroNota.matricula_id, RegistroNota.valor_nota)
        .where(RegistroNota.matricula_id.in_(matricula_ids))
        .order_by(RegistroNota.matricula_id, RegistroNota.data_atualizacao)
    )).all():
        notas_por_matricula.setdefault(matricula_id, []).append(float(valor_nota))

    # --- Sinal 3: mensalidades vencidas e ainda por pagar ---
    hoje = date.today()
    atraso_por_matricula = dict((await db.execute(
        select(ContratoFinanceiro.matricula_id, func.count(FaturaMensalidade.id))
        .join(FaturaMensalidade, FaturaMensalidade.contrato_id == ContratoFinanceiro.id)
        .where(
            ContratoFinanceiro.matricula_id.in_(matricula_ids),
            FaturaMensalidade.status_pagamento == "PENDENTE",
            FaturaMensalidade.data_vencimento < hoje,
        )
        .group_by(ContratoFinanceiro.matricula_id)
    )).all())

    resultado = []
    for matricula_id, aluno_id, nome_aluno, nome_turma in matriculas:
        pontos = 0
        fatores = []

        faltas, aulas = freq_por_matricula.get(matricula_id, (0, 0))
        taxa_falta = (faltas / aulas) if aulas else 0.0
        if taxa_falta >= LIMIAR_FALTA_ALTA:
            pontos += PONTOS_FALTA_ALTA
            fatores.append(f"Faltas elevadas ({round(taxa_falta * 100)}% das aulas)")
        elif taxa_falta >= LIMIAR_FALTA_MEDIA:
            pontos += PONTOS_FALTA_MEDIA
            fatores.append(f"Faltas acima do normal ({round(taxa_falta * 100)}% das aulas)")

        notas = notas_por_matricula.get(matricula_id, [])
        media_notas = round(sum(notas) / len(notas), 2) if notas else None
        if len(notas) >= 2:
            metade = len(notas) // 2
            media_antiga = sum(notas[:metade]) / metade
            media_recente = sum(notas[metade:]) / (len(notas) - metade)
            if media_antiga > 0 and media_recente <= media_antiga * LIMIAR_QUEDA_NOTAS:
                pontos += PONTOS_QUEDA_NOTAS
                fatores.append("Queda no rendimento escolar")

        qtd_atraso = atraso_por_matricula.get(matricula_id, 0)
        if qtd_atraso >= 2:
            pontos += PONTOS_ATRASO_GRAVE
            fatores.append(f"{qtd_atraso} mensalidades vencidas por pagar")
        elif qtd_atraso == 1:
            pontos += PONTOS_ATRASO_LEVE
            fatores.append("1 mensalidade vencida por pagar")

        if pontos == 0:
            continue

        nivel_risco = "ALTO" if pontos >= LIMIAR_RISCO_ALTO else "MEDIO" if pontos >= LIMIAR_RISCO_MEDIO else "BAIXO"
        resultado.append({
            "aluno_id": aluno_id,
            "matricula_id": matricula_id,
            "nome_aluno": nome_aluno,
            "nome_turma": nome_turma,
            "pontuacao_risco": min(pontos, 100),
            "nivel_risco": nivel_risco,
            "fatores": fatores,
            "taxa_falta": round(taxa_falta * 100, 1),
            "media_notas": media_notas,
            "mensalidades_em_atraso": qtd_atraso,
        })

    resultado.sort(key=lambda linha: linha["pontuacao_risco"], reverse=True)
    return resultado


# ==========================================
# H. AGREGADO GERAL DO PAINEL
# ==========================================
async def obter_indicadores(db: AsyncSession, tenant_id) -> dict:
    risco_evasao = await obter_risco_evasao(db, tenant_id)
    return {
        "academico": await obter_resumo_academico(db, tenant_id),
        "desempenho_por_turma": await obter_desempenho_por_turma(db, tenant_id),
        "eficiencia_por_objetivo": await obter_eficiencia_por_objetivo(db, tenant_id),
        "financeiro": await obter_resumo_financeiro(db, tenant_id),
        "crm": await obter_funil_crm(db, tenant_id),
        # No agregado só o resumo (a lista completa tem o seu próprio
        # endpoint, GET /indicadores/risco-evasao, para não sobrecarregar
        # o payload do painel principal com o detalhe de cada aluno).
        "risco_evasao_resumo": {
            "total_alto": sum(1 for r in risco_evasao if r["nivel_risco"] == "ALTO"),
            "total_medio": sum(1 for r in risco_evasao if r["nivel_risco"] == "MEDIO"),
            "total_baixo": sum(1 for r in risco_evasao if r["nivel_risco"] == "BAIXO"),
        },
    }


# ==========================================
# J. RELATÓRIO (PDF) E EXPORTAÇÃO (CSV)
# ==========================================
async def gerar_pdf_relatorio(db: AsyncSession, tenant_id) -> bytes:
    """Fotografia completa do painel em PDF (A4) — reaproveita
    obter_indicadores/obter_risco_evasao tal-e-qual, só achata os
    dicionários aninhados (academico/financeiro/crm) num único
    contexto, porque o template não precisa de repetir esses prefixos.
    Não é personalizável por escola (ver documentos_pdf.py) — é um
    relatório de gestão interna, não um documento com a identidade da
    escola que a família vê."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    dados = await obter_indicadores(db, tenant_id)
    risco_evasao = await obter_risco_evasao(db, tenant_id)

    contexto = {
        **dados["academico"],
        **dados["financeiro"],
        **dados["crm"],
        "funil_crm": dados["crm"]["funil"],
        "desempenho_por_turma": dados["desempenho_por_turma"],
        "eficiencia_por_objetivo": dados["eficiencia_por_objetivo"],
        "risco_total_alto": dados["risco_evasao_resumo"]["total_alto"],
        "risco_evasao": risco_evasao,
        "moeda": tenant.moeda if tenant else "",
    }
    escola = {
        "nome": tenant.nome_fantasia if tenant else "",
        "logo_data_uri": await storage.obter_logo_data_uri(tenant) if tenant else None,
    }
    return documentos_pdf.gerar_pdf_relatorio_indicadores(escola, contexto)


async def gerar_csv_risco_evasao(db: AsyncSession, tenant_id) -> str:
    """CSV da lista de Risco de Evasão — a secção mais "tabular" do
    painel (uma linha por aluno), a que mais vale a pena levar para
    Excel/Google Sheets para filtrar/partilhar com a equipa pedagógica.
    utf-8-sig (BOM) para o Excel abrir acentos corretamente sem o
    utilizador ter de escolher a codificação manualmente."""
    linhas = await obter_risco_evasao(db, tenant_id)
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["Aluno", "Turma", "Nível de risco", "Pontuação", "Fatores", "Taxa de faltas (%)", "Média de notas", "Mensalidades em atraso"])
    for linha in linhas:
        escritor.writerow([
            linha["nome_aluno"], linha["nome_turma"], linha["nivel_risco"], linha["pontuacao_risco"],
            "; ".join(linha["fatores"]), linha["taxa_falta"],
            linha["media_notas"] if linha["media_notas"] is not None else "",
            linha["mensalidades_em_atraso"],
        ])
    return "﻿" + buffer.getvalue()


# ==========================================
# I. TRILHAS DE RECUPERAÇÃO (Prof. Virtual / IA) — só para alunos já sinalizados por G
# ==========================================
async def gerar_trilha_recuperacao(db: AsyncSession, tenant_id, matricula_id, usuario_id) -> TrilhaRecuperacao:
    """
    Pede ao Prof. Virtual (IA) um plano de recuperação para um aluno já
    sinalizado pelo motor de risco de evasão. Reaproveita
    obter_risco_evasao em vez de recalcular os sinais aqui — assim o
    prompt vê exatamente os mesmos fatores que o Gestor vê no ecrã, sem
    duas fontes de verdade sobre o risco deste aluno.
    """
    perfil = next((r for r in await obter_risco_evasao(db, tenant_id) if r["matricula_id"] == matricula_id), None)
    if not perfil:
        raise HTTPException(
            status_code=400,
            detail="Este aluno não tem sinais de risco de evasão no momento — não há trilha de recuperação a gerar."
        )

    conteudo = await prof_virtual.gerar_trilha_recuperacao(
        nome_aluno=perfil["nome_aluno"],
        nome_turma=perfil["nome_turma"],
        nivel_risco=perfil["nivel_risco"],
        pontuacao_risco=perfil["pontuacao_risco"],
        fatores=perfil["fatores"],
        taxa_falta=perfil["taxa_falta"],
        media_notas=perfil["media_notas"],
    )

    nova_trilha = TrilhaRecuperacao(
        tenant_id=tenant_id,
        aluno_id=perfil["aluno_id"],
        matricula_id=matricula_id,
        gerada_por=usuario_id,
        pontuacao_risco_momento=perfil["pontuacao_risco"],
        nivel_risco_momento=perfil["nivel_risco"],
        conteudo=conteudo,
    )
    db.add(nova_trilha)
    await db.commit()
    await db.refresh(nova_trilha)
    return nova_trilha


async def listar_trilhas_do_aluno(db: AsyncSession, tenant_id, matricula_id) -> list[TrilhaRecuperacao]:
    """Histórico de trilhas já geradas para este aluno, mais recente primeiro — para não gerar (e pagar) outra vez sem necessidade."""
    return list((await db.execute(
        select(TrilhaRecuperacao)
        .where(TrilhaRecuperacao.tenant_id == tenant_id, TrilhaRecuperacao.matricula_id == matricula_id)
        .order_by(TrilhaRecuperacao.data_criacao.desc())
    )).scalars().all())
