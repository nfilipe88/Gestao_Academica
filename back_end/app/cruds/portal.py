"""
Acesso a dados do Portal do Aluno/Responsável — vista de leitura,
agregando dados já produzidos por outros módulos (Diário, Horários,
Financeiro) para os logins ALUNO/RESPONSAVEL, sempre restrita aos
seus próprios educandos.

Este módulo não duplica regras de negócio: só resolve "que aluno_id(s)
este login pode ver" e delega a leitura em si aos cruds já existentes
(cruds/horarios.py, cruds/financeiro.py), que continuam a ser os
únicos donos das suas tabelas.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_academico import Disciplina, Turma
from app.database.models_diario import RegistroFrequencia, RegistroNota
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.cruds import financeiro as crud_financeiro
from app.cruds import horarios as crud_horarios


# ==========================================
# RESOLUÇÃO DE ACESSO (que aluno_id este login pode ver)
# ==========================================
async def _resolver_meus_alunos(db: AsyncSession, tenant_id, utilizador: dict) -> list[uuid.UUID]:
    perfil = utilizador.get("perfil_acesso")
    if perfil == "ALUNO":
        aluno_id = (await db.execute(
            select(Aluno.id).where(Aluno.usuario_id == utilizador["usuario_id"], Aluno.tenant_id == tenant_id)
        )).scalar_one_or_none()
        return [aluno_id] if aluno_id else []
    if perfil == "RESPONSAVEL":
        responsavel_id = (await db.execute(
            select(ResponsavelFinanceiroLegal.id).where(
                ResponsavelFinanceiroLegal.usuario_id == utilizador["usuario_id"],
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if not responsavel_id:
            return []
        ids = (await db.execute(
            select(AlunoResponsavel.aluno_id).where(AlunoResponsavel.responsavel_id == responsavel_id)
        )).scalars().all()
        return list(ids)
    return []


async def _garantir_aluno_permitido(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> Aluno:
    permitidos = await _resolver_meus_alunos(db, tenant_id, utilizador)
    if aluno_id not in permitidos:
        raise HTTPException(status_code=403, detail="Sem acesso a este aluno.")
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
    return aluno


async def _obter_matricula_atual(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> Matricula | None:
    """
    A matrícula "atual" do aluno para efeitos do Portal: prioriza uma
    matrícula ATIVO (a mais recente, se houver mais que uma) e só cai
    para a mais recente de qualquer status se não houver nenhuma ativa
    — a data de criação sozinha não é fiável aqui (uma matrícula
    ATIVO mais antiga continua a ser "a atual" mesmo que exista um
    registo TRANCADO/TRANSFERIDO mais recente).
    """
    ordem = (Matricula.ano_letivo.desc(), Matricula.data_matricula.desc())
    ativa = (await db.execute(
        select(Matricula)
        .where(Matricula.aluno_id == aluno_id, Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO")
        .order_by(*ordem)
    )).scalars().first()
    if ativa:
        return ativa
    return (await db.execute(
        select(Matricula)
        .where(Matricula.aluno_id == aluno_id, Matricula.tenant_id == tenant_id)
        .order_by(*ordem)
    )).scalars().first()


# ==========================================
# A. MEUS EDUCANDOS
# ==========================================
async def listar_meus_educandos(db: AsyncSession, tenant_id, utilizador: dict) -> list[dict]:
    aluno_ids = await _resolver_meus_alunos(db, tenant_id, utilizador)
    if not aluno_ids:
        return []

    alunos = (await db.execute(
        select(Aluno).where(Aluno.id.in_(aluno_ids), Aluno.tenant_id == tenant_id)
    )).scalars().all()

    resultado = []
    for aluno in alunos:
        matricula = await _obter_matricula_atual(db, tenant_id, aluno.id)
        nome_turma = None
        if matricula:
            nome_turma = (await db.execute(
                select(Turma.nome_codigo).where(Turma.id == matricula.turma_id)
            )).scalar_one_or_none()
        resultado.append({
            "aluno_id": aluno.id,
            "nome_completo": aluno.nome_completo,
            "matricula_interna": aluno.matricula_interna,
            "matricula_id": matricula.id if matricula else None,
            "status_matricula": matricula.status_matricula if matricula else None,
            "ano_letivo": matricula.ano_letivo if matricula else None,
            "nome_turma": nome_turma,
        })
    return resultado


# ==========================================
# B. HORÁRIO DO EDUCANDO
# ==========================================
async def obter_horario_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        return []
    return await crud_horarios.listar_grade_da_turma(db, tenant_id, matricula.turma_id)


# ==========================================
# C. BOLETIM (NOTAS + FREQUÊNCIA) DO EDUCANDO
# ==========================================
async def obter_boletim_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> dict:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        return {"disciplinas": []}

    notas = (await db.execute(
        select(RegistroNota, Disciplina.nome)
        .join(Disciplina, Disciplina.id == RegistroNota.disciplina_id)
        .where(RegistroNota.matricula_id == matricula.id, RegistroNota.tenant_id == tenant_id)
        .order_by(Disciplina.nome, RegistroNota.periodo_avaliacao)
    )).all()

    frequencias = (await db.execute(
        select(
            RegistroFrequencia.disciplina_id, Disciplina.nome,
            func.count(RegistroFrequencia.id), func.sum(RegistroFrequencia.faltas)
        )
        .join(Disciplina, Disciplina.id == RegistroFrequencia.disciplina_id)
        .where(RegistroFrequencia.matricula_id == matricula.id, RegistroFrequencia.tenant_id == tenant_id)
        .group_by(RegistroFrequencia.disciplina_id, Disciplina.nome)
    )).all()

    por_disciplina: dict[uuid.UUID, dict] = {}

    def _entrada(disciplina_id: uuid.UUID, nome_disciplina: str) -> dict:
        return por_disciplina.setdefault(disciplina_id, {
            "disciplina_id": disciplina_id,
            "nome_disciplina": nome_disciplina,
            "notas": [],
            "total_aulas": 0,
            "total_faltas": 0,
        })

    for nota, nome_disciplina in notas:
        entrada = _entrada(nota.disciplina_id, nome_disciplina)
        entrada["notas"].append({
            "periodo_avaliacao": nota.periodo_avaliacao,
            "tipo_avaliacao": nota.tipo_avaliacao,
            "data_avaliacao": nota.data_avaliacao,
            "valor_nota": nota.valor_nota,
        })

    for disciplina_id, nome_disciplina, total_aulas, total_faltas in frequencias:
        entrada = _entrada(disciplina_id, nome_disciplina)
        entrada["total_aulas"] = int(total_aulas or 0)
        entrada["total_faltas"] = int(total_faltas or 0)

    return {"disciplinas": sorted(por_disciplina.values(), key=lambda d: d["nome_disciplina"])}


# ==========================================
# D. FINANCEIRO (CONTRATO + FATURAS) DO EDUCANDO
# ==========================================
async def obter_financeiro_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> dict:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        return {"matricula_id": None, "contrato": None, "faturas": []}

    try:
        contrato = await crud_financeiro.obter_contrato_da_matricula(db, tenant_id, matricula.id, utilizador)
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"matricula_id": matricula.id, "contrato": None, "faturas": []}
        raise

    faturas = await crud_financeiro.listar_faturas_do_contrato(db, tenant_id, contrato.id, utilizador)
    return {
        "matricula_id": matricula.id,
        "contrato": {
            "id": contrato.id,
            "valor_total_anual": contrato.valor_total_anual,
            "quantidade_parcelas": contrato.quantidade_parcelas,
        },
        "faturas": faturas,
    }
