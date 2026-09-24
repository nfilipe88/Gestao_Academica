"""Resultado final do aluno (fecho do ano letivo) e pendências do trimestre.

Regras (todas configuráveis por escola em Configurações; ver Tenant):
- Média final da disciplina (m_final): MFD = média das notas dos períodos
  (MT) — se houver Exame Nacional lançado, m_final = (MFD + NEN) / 2. É a
  mesma fórmula da Pauta do Portal (calcular_media_final é partilhada).
- Disciplina aprovada: m_final >= Tenant.nota_minima_aprovacao.
- Disciplina INCOMPLETA: falta a nota de algum período registado (ou, se a
  escola não regista períodos, não há nota nenhuma). Um aluno com alguma
  disciplina incompleta fica INCOMPLETO e não pode ser fechado.
- REPROVADO_FALTAS: faltas > Tenant.limite_faltas_percentagem % das aulas
  lecionadas (só se a escola definiu o limite).
- REPROVADO: disciplinas abaixo da nota mínima > Tenant.max_disciplinas_reprovadas.
- APROVADO: caso contrário.
Só matrículas ATIVO entram (transferidos/evadidos/trancados não têm resultado).
Os valores por omissão são técnicos: a escola/direção tem de os confirmar
contra o regulamento que aplica.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_academico import Disciplina, GradeCurricular, Turma
from app.database.models_diario import (
    NotaExameNacional, PeriodoAvaliacao, ProfessorTurmaDisciplina, RegistroFrequencia, RegistroNota,
)
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, Professor

RESULTADOS = ("APROVADO", "REPROVADO", "REPROVADO_FALTAS")


def calcular_media_final(medias_periodo: list, nota_exame_nacional=None) -> tuple[float | None, float | None]:
    """(MFD, M. Final) — MFD = média dos MT; com NEN lançado, M. Final = (MFD+NEN)/2."""
    if not medias_periodo:
        return None, None
    mfd = round(sum(float(m) for m in medias_periodo) / len(medias_periodo), 2)
    if nota_exame_nacional is not None:
        return mfd, round((mfd + float(nota_exame_nacional)) / 2, 2)
    return mfd, mfd


async def _disciplinas_esperadas_por_turma(db: AsyncSession, tenant_id, turmas: list[Turma]) -> dict[uuid.UUID, set]:
    """Grade curricular da série ∪ disciplinas alocadas a professores na turma."""
    esperadas: dict[uuid.UUID, set] = {t.id: set() for t in turmas}
    if not turmas:
        return esperadas
    por_serie: dict[uuid.UUID, list] = {}
    for turma in turmas:
        por_serie.setdefault(turma.serie_ano_id, []).append(turma.id)
    for serie_id, disciplina_id in (await db.execute(
        select(GradeCurricular.serie_ano_id, GradeCurricular.disciplina_id)
        .where(GradeCurricular.tenant_id == tenant_id, GradeCurricular.serie_ano_id.in_(list(por_serie)))
    )).all():
        for turma_id in por_serie[serie_id]:
            esperadas[turma_id].add(disciplina_id)
    for turma_id, disciplina_id in (await db.execute(
        select(ProfessorTurmaDisciplina.turma_id, ProfessorTurmaDisciplina.disciplina_id)
        .where(ProfessorTurmaDisciplina.tenant_id == tenant_id, ProfessorTurmaDisciplina.turma_id.in_([t.id for t in turmas]))
    )).all():
        esperadas[turma_id].add(disciplina_id)
    return esperadas


async def periodos_registados(db: AsyncSession, tenant_id) -> list[PeriodoAvaliacao]:
    return list((await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id).order_by(PeriodoAvaliacao.data_criacao)
    )).scalars().all())


async def calcular_resultados_do_ano(db: AsyncSession, tenant: Tenant, ano_letivo: int) -> list[dict]:
    """Um dicionário por matrícula ATIVO do ano, com o resultado calculado (nada é gravado)."""
    tenant_id = tenant.id
    nota_minima = float(tenant.nota_minima_aprovacao) if tenant.nota_minima_aprovacao is not None else None
    periodos = [p.nome for p in await periodos_registados(db, tenant_id)]

    linhas = (await db.execute(
        select(Matricula, Aluno.nome_completo, Aluno.matricula_interna, Turma)
        .join(Aluno, Aluno.id == Matricula.aluno_id).join(Turma, Turma.id == Matricula.turma_id)
        .where(Matricula.tenant_id == tenant_id, Matricula.ano_letivo == ano_letivo, Matricula.status_matricula == "ATIVO")
        .order_by(Turma.nome_codigo, Aluno.nome_completo)
    )).all()
    if not linhas:
        return []
    matricula_ids = [m.id for m, *_ in linhas]

    esperadas = await _disciplinas_esperadas_por_turma(db, tenant_id, list({t.id: t for *_, t in linhas}.values()))

    notas: dict[tuple, dict[str, float]] = {}
    for matricula_id, disciplina_id, periodo, valor in (await db.execute(
        select(RegistroNota.matricula_id, RegistroNota.disciplina_id, RegistroNota.periodo_avaliacao, RegistroNota.valor_nota)
        .where(RegistroNota.tenant_id == tenant_id, RegistroNota.matricula_id.in_(matricula_ids))
    )).all():
        notas.setdefault((matricula_id, disciplina_id), {})[periodo] = float(valor)

    nen = {(m, d): float(v) for m, d, v in (await db.execute(
        select(NotaExameNacional.matricula_id, NotaExameNacional.disciplina_id, NotaExameNacional.valor_nota)
        .where(NotaExameNacional.tenant_id == tenant_id, NotaExameNacional.matricula_id.in_(matricula_ids))
    )).all()}

    freq = {m: (int(aulas or 0), int(faltas or 0)) for m, aulas, faltas in (await db.execute(
        select(RegistroFrequencia.matricula_id, func.sum(RegistroFrequencia.quantidade_aulas), func.sum(RegistroFrequencia.faltas))
        .where(RegistroFrequencia.tenant_id == tenant_id, RegistroFrequencia.matricula_id.in_(matricula_ids))
        .group_by(RegistroFrequencia.matricula_id)
    )).all()}

    nomes_disciplinas = dict((await db.execute(
        select(Disciplina.id, Disciplina.nome).where(Disciplina.tenant_id == tenant_id)
    )).all())

    resultados = []
    for matricula, nome_aluno, numero, turma in linhas:
        disciplinas_ids = set(esperadas.get(turma.id, set())) | {d for (m, d) in notas if m == matricula.id}
        disciplinas, em_falta = [], []
        for disciplina_id in sorted(disciplinas_ids, key=lambda d: nomes_disciplinas.get(d, "")):
            por_periodo = notas.get((matricula.id, disciplina_id), {})
            exigidos = periodos or list(por_periodo)
            completa = bool(por_periodo) and all(p in por_periodo for p in exigidos)
            mfd, m_final = calcular_media_final(list(por_periodo.values()), nen.get((matricula.id, disciplina_id)))
            nome = nomes_disciplinas.get(disciplina_id, "?")
            if not completa:
                em_falta.append(nome)
            disciplinas.append({
                "disciplina_id": str(disciplina_id), "nome": nome, "mfd": mfd, "m_final": m_final,
                "completa": completa,
                "aprovada": (m_final >= nota_minima) if (completa and m_final is not None and nota_minima is not None) else None,
            })

        aulas, faltas = freq.get(matricula.id, (0, 0))
        faltas_pct = round(faltas * 100 / aulas, 2) if aulas else 0.0
        reprovadas = sum(1 for d in disciplinas if d["aprovada"] is False)

        if em_falta or not disciplinas:
            resultado = "INCOMPLETO"
        elif tenant.limite_faltas_percentagem is not None and faltas_pct > float(tenant.limite_faltas_percentagem):
            resultado = "REPROVADO_FALTAS"
        elif reprovadas > (tenant.max_disciplinas_reprovadas or 0):
            resultado = "REPROVADO"
        else:
            resultado = "APROVADO"

        resultados.append({
            "matricula_id": matricula.id, "aluno_id": matricula.aluno_id, "nome_completo": nome_aluno,
            "matricula_interna": numero, "turma": turma.nome_codigo,
            "resultado_atual": matricula.resultado_final,
            "resultado": resultado, "disciplinas": disciplinas, "em_falta": em_falta,
            "disciplinas_reprovadas": reprovadas, "faltas": faltas, "aulas": aulas, "faltas_percentagem": faltas_pct,
        })
    return resultados


def resumir(resultados: list[dict]) -> dict:
    contagem = {r: 0 for r in (*RESULTADOS, "INCOMPLETO")}
    for r in resultados:
        contagem[r["resultado"]] += 1
    return {"total": len(resultados), **{k.lower(): v for k, v in contagem.items()}}


async def pendencias_do_periodo(db: AsyncSession, tenant_id, periodo_nome: str, ano_letivo: int) -> list[dict]:
    """Por turma × disciplina esperada, quem ainda não tem nota neste período."""
    linhas = (await db.execute(
        select(Matricula.id, Aluno.nome_completo, Turma)
        .join(Aluno, Aluno.id == Matricula.aluno_id).join(Turma, Turma.id == Matricula.turma_id)
        .where(Matricula.tenant_id == tenant_id, Matricula.ano_letivo == ano_letivo, Matricula.status_matricula == "ATIVO")
        .order_by(Aluno.nome_completo)
    )).all()
    if not linhas:
        return []
    turmas = {t.id: t for *_, t in linhas}
    esperadas = await _disciplinas_esperadas_por_turma(db, tenant_id, list(turmas.values()))
    matriculas_da_turma: dict[uuid.UUID, list] = {}
    for matricula_id, nome, turma in linhas:
        matriculas_da_turma.setdefault(turma.id, []).append((matricula_id, nome))

    ids_matriculas = [m for m, *_ in linhas]
    com_nota = {(m, d) for m, d in (await db.execute(
        select(RegistroNota.matricula_id, RegistroNota.disciplina_id)
        .where(RegistroNota.tenant_id == tenant_id, RegistroNota.periodo_avaliacao == periodo_nome,
               RegistroNota.matricula_id.in_(ids_matriculas))
    )).all()}
    # Disciplina sem grade nem alocação mas já com notas de qualquer período da turma também conta.
    turma_da_matricula = {m: t.id for m, _, t in linhas}
    for matricula_id, disciplina_id in (await db.execute(
        select(RegistroNota.matricula_id, RegistroNota.disciplina_id)
        .where(RegistroNota.tenant_id == tenant_id, RegistroNota.matricula_id.in_(ids_matriculas)).distinct()
    )).all():
        esperadas[turma_da_matricula[matricula_id]].add(disciplina_id)
    nomes = dict((await db.execute(select(Disciplina.id, Disciplina.nome).where(Disciplina.tenant_id == tenant_id))).all())
    professores = {}
    for turma_id, disciplina_id, nome_prof in (await db.execute(
        select(ProfessorTurmaDisciplina.turma_id, ProfessorTurmaDisciplina.disciplina_id, Usuario.nome_completo)
        .join(Professor, Professor.id == ProfessorTurmaDisciplina.professor_id)
        .join(Usuario, Usuario.id == Professor.usuario_id)
        .where(ProfessorTurmaDisciplina.tenant_id == tenant_id)
    )).all():
        professores[(turma_id, disciplina_id)] = nome_prof

    pendencias = []
    for turma_id, matriculas in matriculas_da_turma.items():
        for disciplina_id in esperadas.get(turma_id, set()):
            faltam = [nome for matricula_id, nome in matriculas if (matricula_id, disciplina_id) not in com_nota]
            if faltam:
                pendencias.append({
                    "turma": turmas[turma_id].nome_codigo, "disciplina": nomes.get(disciplina_id, "?"),
                    "professor": professores.get((turma_id, disciplina_id)),
                    "total_alunos": len(matriculas), "sem_nota": len(faltam), "alunos_sem_nota": faltam[:30],
                })
    return sorted(pendencias, key=lambda p: (p["turma"], p["disciplina"]))
