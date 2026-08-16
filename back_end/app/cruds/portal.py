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

from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_diario import RegistroFrequencia, RegistroNota
from app.database.models_lms import MaterialAula
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno
from app.cruds import alunos as crud_alunos
from app.cruds import financeiro as crud_financeiro
from app.cruds import horarios as crud_horarios
from app.cruds import tarefas as crud_tarefas
from app.core.prof_virtual import perguntar_prof_virtual
from app.schemas.lms import ProfVirtualPerguntaCreate

# Resolução de acesso ("que aluno_id este login pode ver") vive em
# cruds/alunos.py — também é precisa em Documentos (pedidos do
# aluno/responsável), por isso deixou de estar duplicada aqui.
_resolver_meus_alunos = crud_alunos.resolver_meus_alunos
_garantir_aluno_permitido = crud_alunos.garantir_aluno_permitido


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


# ==========================================
# E. TRABALHOS/TAREFAS DO EDUCANDO
# ==========================================
async def listar_tarefas_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        return []
    return await crud_tarefas.listar_tarefas_do_aluno(db, tenant_id, matricula.id)


# ==========================================
# F. MATERIAIS DE AULA (LMS mínimo) + PROF. VIRTUAL
# ==========================================
async def listar_materiais_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    """Materiais publicados para a turma atual do educando, agrupáveis por disciplina no front-end."""
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        return []

    linhas = (await db.execute(
        select(MaterialAula, Disciplina.nome)
        .join(Disciplina, Disciplina.id == MaterialAula.disciplina_id)
        .where(
            MaterialAula.turma_id == matricula.turma_id,
            MaterialAula.tenant_id == tenant_id,
            MaterialAula.publicado.is_(True)
        )
        .order_by(Disciplina.nome, MaterialAula.data_criacao.desc())
    )).all()

    return [
        {
            "id": material.id,
            "titulo": material.titulo,
            "disciplina_id": material.disciplina_id,
            "nome_disciplina": nome_disciplina,
            "data_criacao": material.data_criacao,
        }
        for material, nome_disciplina in linhas
    ]


async def _obter_material_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, material_id: uuid.UUID) -> MaterialAula:
    """Devolve o MaterialAula só se pertencer à turma atual do educando e estiver publicado — nunca deixa ver o de outra turma trocando o id no URL."""
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        raise HTTPException(status_code=404, detail="Material de aula não encontrado.")

    material = (await db.execute(
        select(MaterialAula).where(
            MaterialAula.id == material_id,
            MaterialAula.tenant_id == tenant_id,
            MaterialAula.turma_id == matricula.turma_id,
            MaterialAula.publicado.is_(True)
        )
    )).scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Material de aula não encontrado.")
    return material


async def obter_material_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, material_id: uuid.UUID) -> dict:
    material = await _obter_material_do_educando(db, tenant_id, utilizador, aluno_id, material_id)
    nome_objetivo = None
    if material.objetivo_aprendizagem_id:
        nome_objetivo = (await db.execute(
            select(ObjetivoAprendizagem.nome).where(ObjetivoAprendizagem.id == material.objetivo_aprendizagem_id)
        )).scalar_one_or_none()
    return {
        "id": material.id,
        "titulo": material.titulo,
        "corpo": material.corpo,
        "disciplina_id": material.disciplina_id,
        "nome_objetivo": nome_objetivo,
    }


async def perguntar_prof_virtual_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, dados: ProfVirtualPerguntaCreate) -> str:
    """Encaminha a pergunta do aluno ao Prof. Virtual, com o material como contexto — a posse do material já garante que o aluno só pergunta sobre a sua própria turma."""
    material = await _obter_material_do_educando(db, tenant_id, utilizador, aluno_id, dados.material_id)
    nome_objetivo = None
    if material.objetivo_aprendizagem_id:
        nome_objetivo = (await db.execute(
            select(ObjetivoAprendizagem.nome).where(ObjetivoAprendizagem.id == material.objetivo_aprendizagem_id)
        )).scalar_one_or_none()

    return await perguntar_prof_virtual(
        titulo_material=material.titulo,
        corpo_material=material.corpo,
        nome_objetivo=nome_objetivo,
        historico=dados.historico,
        pergunta=dados.pergunta
    )
