"""
Acesso a dados da área de Estatísticas — um Dashboard com o estado
corrente da escola, mais um Relatório filtrável por intervalo de
datas (exportável em .xlsx/.xls, ver app/core/estatisticas_excel.py).

Distinto de Indicadores (app/cruds/indicadores.py): Indicadores é uma
visão executiva "tudo em tempo real, sem filtros"; Estatísticas
existe especificamente para o Gestor escolher um período e tirar um
documento — por isso quase tudo aqui aceita data_inicio/data_fim
opcionais (None = sem filtro, para o Dashboard).

Tal como Indicadores, não introduz nenhuma regra de negócio própria —
só agregação (COUNT/AVG/SUM) sobre dados já produzidos por outros
módulos. A única tabela nova associada a esta funcionalidade é
Despesa (ver cruds/financeiro.py), a contrapartida das Entradas que
faltava para as estatísticas financeiras poderem mostrar saídas reais
— sem isso, "maiores saídas" não tinha nenhum dado na plataforma.
"""
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_academico import Curso, Disciplina, SerieAno, Turma
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno
from app.database.models_financeiro import ContratoFinanceiro, Despesa, FaturaMensalidade
from app.database.models_diario import RegistroNota
from app.cruds import financeiro as crud_financeiro

# Nº de linhas em cada lista "top N" (cursos/disciplinas/turmas/alunos/
# entradas/saídas) — o mesmo limite em todo o lado, para não haver
# relatórios com tamanhos inconsistentes entre secções.
LIMITE_RANKING = 10

FAIXAS_ETARIAS = [("5-9", 5, 9), ("10-14", 10, 14), ("15-18", 15, 18), ("19+", 19, None)]


def _calcular_idade(data_nascimento: date, referencia: date) -> int:
    return referencia.year - data_nascimento.year - (
        (referencia.month, referencia.day) < (data_nascimento.month, data_nascimento.day)
    )


def _inicio_do_dia(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _fim_do_dia(d: date) -> datetime:
    return datetime.combine(d, time.max)


# ==========================================
# A. ACADÉMICO
# ==========================================
async def _obter_total_matriculados(db: AsyncSession, tenant_id) -> int:
    return (await db.execute(
        select(func.count(func.distinct(Matricula.aluno_id))).where(
            Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO"
        )
    )).scalar_one()


async def _obter_faixas_etarias(db: AsyncSession, tenant_id) -> list[dict]:
    linhas = (await db.execute(
        select(Aluno.id, Aluno.data_nascimento)
        .join(Matricula, Matricula.aluno_id == Aluno.id)
        .where(Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO")
        .distinct()
    )).all()
    hoje = date.today()
    idades = [_calcular_idade(data_nascimento, hoje) for _, data_nascimento in linhas]

    resultado = []
    for rotulo, minimo, maximo in FAIXAS_ETARIAS:
        if maximo is None:
            total = sum(1 for i in idades if i >= minimo)
        else:
            total = sum(1 for i in idades if minimo <= i <= maximo)
        resultado.append({"faixa": rotulo, "total": total})
    return resultado


async def _obter_cursos_mais_concorridos(db: AsyncSession, tenant_id) -> list[dict]:
    """Ranking por matrículas ATIVO atuais — não faz sentido filtrado por
    data_matricula (um curso "concorrido" é sobre quem lá está agora,
    não sobre quantas matrículas entraram num período)."""
    resultado = await db.execute(
        select(Curso.id, Curso.nome, func.count(Matricula.id))
        .join(SerieAno, SerieAno.curso_id == Curso.id)
        .join(Turma, Turma.serie_ano_id == SerieAno.id)
        .join(Matricula, (Matricula.turma_id == Turma.id) & (Matricula.status_matricula == "ATIVO"))
        .where(Curso.tenant_id == tenant_id)
        .group_by(Curso.id, Curso.nome)
        .order_by(func.count(Matricula.id).desc())
        .limit(LIMITE_RANKING)
    )
    return [
        {"curso_id": curso_id, "nome_curso": nome, "total_matriculados": total}
        for curso_id, nome, total in resultado.all()
    ]


async def _obter_disciplinas_maior_aproveitamento(
    db: AsyncSession, tenant_id, data_inicio: date | None, data_fim: date | None
) -> list[dict]:
    query = (
        select(Disciplina.id, Disciplina.nome, func.avg(RegistroNota.valor_nota), func.count(RegistroNota.id))
        .join(RegistroNota, RegistroNota.disciplina_id == Disciplina.id)
        .where(Disciplina.tenant_id == tenant_id)
    )
    if data_inicio:
        query = query.where(RegistroNota.data_avaliacao >= data_inicio)
    if data_fim:
        query = query.where(RegistroNota.data_avaliacao <= data_fim)
    query = query.group_by(Disciplina.id, Disciplina.nome).order_by(func.avg(RegistroNota.valor_nota).desc()).limit(LIMITE_RANKING)

    resultado = await db.execute(query)
    return [
        {"disciplina_id": did, "nome_disciplina": nome, "media": round(float(media), 2), "total_notas": total}
        for did, nome, media, total in resultado.all()
    ]


async def _obter_turmas_melhores_notas(
    db: AsyncSession, tenant_id, data_inicio: date | None, data_fim: date | None
) -> list[dict]:
    query = (
        select(
            Turma.id, Turma.nome_codigo,
            func.avg(RegistroNota.valor_nota), func.count(func.distinct(RegistroNota.matricula_id))
        )
        .join(Matricula, Matricula.turma_id == Turma.id)
        .join(RegistroNota, RegistroNota.matricula_id == Matricula.id)
        .where(Turma.tenant_id == tenant_id)
    )
    if data_inicio:
        query = query.where(RegistroNota.data_avaliacao >= data_inicio)
    if data_fim:
        query = query.where(RegistroNota.data_avaliacao <= data_fim)
    query = query.group_by(Turma.id, Turma.nome_codigo).order_by(func.avg(RegistroNota.valor_nota).desc()).limit(LIMITE_RANKING)

    resultado = await db.execute(query)
    return [
        {"turma_id": tid, "nome_turma": nome, "media": round(float(media), 2), "total_alunos_avaliados": total}
        for tid, nome, media, total in resultado.all()
    ]


async def _obter_alunos_melhores_notas(
    db: AsyncSession, tenant_id, data_inicio: date | None, data_fim: date | None
) -> list[dict]:
    query = (
        select(Aluno.id, Aluno.nome_completo, func.avg(RegistroNota.valor_nota), func.count(RegistroNota.id))
        .join(Matricula, Matricula.aluno_id == Aluno.id)
        .join(RegistroNota, RegistroNota.matricula_id == Matricula.id)
        .where(Aluno.tenant_id == tenant_id)
    )
    if data_inicio:
        query = query.where(RegistroNota.data_avaliacao >= data_inicio)
    if data_fim:
        query = query.where(RegistroNota.data_avaliacao <= data_fim)
    query = query.group_by(Aluno.id, Aluno.nome_completo).order_by(func.avg(RegistroNota.valor_nota).desc()).limit(LIMITE_RANKING)

    resultado = await db.execute(query)
    return [
        {"aluno_id": aid, "nome_aluno": nome, "media": round(float(media), 2), "total_notas": total}
        for aid, nome, media, total in resultado.all()
    ]


# ==========================================
# B. FINANCEIRO
# ==========================================
async def _obter_pagamentos_por_mes(db: AsyncSession, tenant_id, data_inicio: date, data_fim: date) -> list[dict]:
    # .label("mes") + group_by/order_by pelo MESMO objeto Python (não uma
    # segunda chamada a func.to_char(...)) — o Postgres só aceita ORDER BY
    # por algo textualmente idêntico ao que está no GROUP BY/SELECT;
    # duas chamadas a func.to_char(...) construídas em separado geram SQL
    # igual mas o SQLAlchemy não as trata como "a mesma expressão" para
    # esse efeito, e o Postgres rejeitava com GroupingError.
    coluna_mes = func.to_char(FaturaMensalidade.data_pagamento_realizado, 'YYYY-MM').label("mes")
    resultado = await db.execute(
        select(coluna_mes, func.count(FaturaMensalidade.id), func.sum(FaturaMensalidade.valor_pago_realizado))
        .where(
            FaturaMensalidade.tenant_id == tenant_id,
            FaturaMensalidade.status_pagamento == "PAGO",
            FaturaMensalidade.data_pagamento_realizado >= _inicio_do_dia(data_inicio),
            FaturaMensalidade.data_pagamento_realizado <= _fim_do_dia(data_fim),
        )
        .group_by(coluna_mes)
        .order_by(coluna_mes)
    )
    return [
        {"mes": mes, "total_pagamentos": total, "valor_total": valor or Decimal("0.00")}
        for mes, total, valor in resultado.all()
    ]


async def _obter_atrasos_periodo(db: AsyncSession, tenant_id, data_inicio: date, data_fim: date) -> dict:
    faturas = (await db.execute(
        select(FaturaMensalidade).where(
            FaturaMensalidade.tenant_id == tenant_id,
            FaturaMensalidade.status_pagamento == "PENDENTE",
            FaturaMensalidade.data_vencimento >= data_inicio,
            FaturaMensalidade.data_vencimento <= data_fim,
        )
    )).scalars().all()

    total_atrasadas = 0
    valor_total_atraso = Decimal("0.00")
    for fatura in faturas:
        situacao = crud_financeiro.calcular_situacao_fatura(fatura)
        if situacao["status_efetivo"] == "ATRASADO":
            total_atrasadas += 1
            valor_total_atraso += situacao["valor_atualizado"]
    return {"total_faturas_atrasadas": total_atrasadas, "valor_total_atraso": valor_total_atraso}


async def _obter_maiores_entradas(db: AsyncSession, tenant_id, data_inicio: date, data_fim: date) -> list[dict]:
    resultado = await db.execute(
        select(
            FaturaMensalidade.id, FaturaMensalidade.valor_pago_realizado, FaturaMensalidade.data_pagamento_realizado,
            FaturaMensalidade.forma_pagamento, Aluno.nome_completo
        )
        .join(ContratoFinanceiro, ContratoFinanceiro.id == FaturaMensalidade.contrato_id)
        .join(Matricula, Matricula.id == ContratoFinanceiro.matricula_id)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(
            FaturaMensalidade.tenant_id == tenant_id,
            FaturaMensalidade.status_pagamento == "PAGO",
            FaturaMensalidade.data_pagamento_realizado >= _inicio_do_dia(data_inicio),
            FaturaMensalidade.data_pagamento_realizado <= _fim_do_dia(data_fim),
        )
        .order_by(FaturaMensalidade.valor_pago_realizado.desc())
        .limit(LIMITE_RANKING)
    )
    return [
        {
            "fatura_id": fid, "nome_aluno": nome_aluno, "valor": valor,
            "data_pagamento": data_pagamento, "forma_pagamento": forma_pagamento,
        }
        for fid, valor, data_pagamento, forma_pagamento, nome_aluno in resultado.all()
    ]


async def _obter_despesas_por_mes(db: AsyncSession, tenant_id, data_inicio: date, data_fim: date) -> list[dict]:
    coluna_mes = func.to_char(Despesa.data_despesa, 'YYYY-MM').label("mes")  # ver nota em _obter_pagamentos_por_mes
    resultado = await db.execute(
        select(coluna_mes, func.count(Despesa.id), func.sum(Despesa.valor))
        .where(Despesa.tenant_id == tenant_id, Despesa.data_despesa >= data_inicio, Despesa.data_despesa <= data_fim)
        .group_by(coluna_mes)
        .order_by(coluna_mes)
    )
    return [{"mes": mes, "total_despesas": total, "valor_total": valor} for mes, total, valor in resultado.all()]


async def _obter_maiores_saidas(db: AsyncSession, tenant_id, data_inicio: date, data_fim: date) -> list[dict]:
    resultado = await db.execute(
        select(Despesa.id, Despesa.categoria, Despesa.descricao, Despesa.valor, Despesa.data_despesa)
        .where(Despesa.tenant_id == tenant_id, Despesa.data_despesa >= data_inicio, Despesa.data_despesa <= data_fim)
        .order_by(Despesa.valor.desc())
        .limit(LIMITE_RANKING)
    )
    return [
        {"despesa_id": did, "categoria": categoria, "descricao": descricao, "valor": valor, "data_despesa": data_despesa}
        for did, categoria, descricao, valor, data_despesa in resultado.all()
    ]


async def _obter_resumo_financeiro_atual(db: AsyncSession, tenant_id) -> dict:
    """Estado corrente (sem filtro de datas) — para o Dashboard."""
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

    contratos_ativos = (await db.execute(
        select(func.count(ContratoFinanceiro.id)).where(ContratoFinanceiro.tenant_id == tenant_id)
    )).scalar_one()

    return {
        "faturas_em_aberto": len(faturas_em_aberto),
        "faturas_atrasadas": total_atrasadas,
        "valor_total_atraso": valor_total_atraso,
        "contratos_ativos": contratos_ativos,
    }


# ==========================================
# C. DASHBOARD (estado corrente, sem filtro de datas)
# ==========================================
async def obter_dashboard(db: AsyncSession, tenant_id) -> dict:
    return {
        "total_alunos_matriculados": await _obter_total_matriculados(db, tenant_id),
        "faixas_etarias": await _obter_faixas_etarias(db, tenant_id),
        "cursos_mais_concorridos": await _obter_cursos_mais_concorridos(db, tenant_id),
        "disciplinas_maior_aproveitamento": await _obter_disciplinas_maior_aproveitamento(db, tenant_id, None, None),
        "turmas_melhores_notas": await _obter_turmas_melhores_notas(db, tenant_id, None, None),
        "alunos_melhores_notas": await _obter_alunos_melhores_notas(db, tenant_id, None, None),
        "resumo_financeiro": await _obter_resumo_financeiro_atual(db, tenant_id),
    }


# ==========================================
# D. RELATÓRIO POR INTERVALO DE DATAS (exportável)
# ==========================================
async def obter_relatorio(db: AsyncSession, tenant_id, data_inicio: date, data_fim: date) -> dict:
    if data_fim < data_inicio:
        raise HTTPException(status_code=400, detail="data_fim tem de ser igual ou posterior a data_inicio.")

    matriculas_no_periodo = (await db.execute(
        select(func.count(Matricula.id)).where(
            Matricula.tenant_id == tenant_id,
            Matricula.data_matricula >= _inicio_do_dia(data_inicio),
            Matricula.data_matricula <= _fim_do_dia(data_fim),
        )
    )).scalar_one()

    pagamentos_por_mes = await _obter_pagamentos_por_mes(db, tenant_id, data_inicio, data_fim)
    despesas_por_mes = await _obter_despesas_por_mes(db, tenant_id, data_inicio, data_fim)
    total_entradas = sum((p["valor_total"] or Decimal("0.00")) for p in pagamentos_por_mes)
    total_saidas = sum((d["valor_total"] or Decimal("0.00")) for d in despesas_por_mes)

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_alunos_matriculados": await _obter_total_matriculados(db, tenant_id),
        "matriculas_no_periodo": matriculas_no_periodo,
        "faixas_etarias": await _obter_faixas_etarias(db, tenant_id),
        "cursos_mais_concorridos": await _obter_cursos_mais_concorridos(db, tenant_id),
        "disciplinas_maior_aproveitamento": await _obter_disciplinas_maior_aproveitamento(db, tenant_id, data_inicio, data_fim),
        "turmas_melhores_notas": await _obter_turmas_melhores_notas(db, tenant_id, data_inicio, data_fim),
        "alunos_melhores_notas": await _obter_alunos_melhores_notas(db, tenant_id, data_inicio, data_fim),
        "pagamentos_por_mes": pagamentos_por_mes,
        "atrasos_periodo": await _obter_atrasos_periodo(db, tenant_id, data_inicio, data_fim),
        "maiores_entradas": await _obter_maiores_entradas(db, tenant_id, data_inicio, data_fim),
        "despesas_por_mes": despesas_por_mes,
        "maiores_saidas": await _obter_maiores_saidas(db, tenant_id, data_inicio, data_fim),
        "total_entradas_periodo": total_entradas,
        "total_saidas_periodo": total_saidas,
        "saldo_periodo": total_entradas - total_saidas,
    }
