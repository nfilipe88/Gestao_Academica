"""
Acesso a dados e regras de negócio da grade horária (Horários).

RN01 - Sem sobreposição na mesma Turma: duas aulas da mesma turma não
podem ter horários que se cruzem no mesmo dia, mesmo que disciplinas
diferentes (um aluno não pode estar em duas aulas ao mesmo tempo).

RN02 - Sem sobreposição do mesmo Professor: um professor não pode
lecionar duas aulas (em turmas diferentes ou não) que se cruzem no
mesmo dia (a mesma pessoa não pode estar em dois sítios ao mesmo tempo).

Cada slot liga-se a uma Alocação (Professor_Turma_Disciplina) já
existente — nunca se guarda professor_id/turma_id/disciplina_id aqui
diretamente, para a grade nunca conseguir agendar uma combinação que
não seja uma alocação real.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.models import Usuario
from app.database.models_academico import Disciplina, Turma
from app.database.models_pessoas import Professor
from app.database.models_diario import ProfessorTurmaDisciplina
from app.database.models_horarios import HorarioAula
from app.schemas.horarios import HorarioAulaCreate, HorarioAulaUpdate


async def _obter_alocacao(db: AsyncSession, tenant_id, alocacao_id: uuid.UUID) -> ProfessorTurmaDisciplina:
    alocacao = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.id == alocacao_id, ProfessorTurmaDisciplina.tenant_id == tenant_id
        )
    )).scalars().first()
    if not alocacao:
        raise HTTPException(status_code=404, detail="Alocação (Professor/Turma/Disciplina) não encontrada na sua instituição.")
    return alocacao


async def _validar_sem_conflito(
    db: AsyncSession, tenant_id, alocacao: ProfessorTurmaDisciplina,
    dia_semana: int, hora_inicio, hora_fim, ignorar_horario_id: uuid.UUID | None = None
) -> None:
    """RN01 (turma) + RN02 (professor): nenhum outro slot no mesmo dia pode sobrepor-se a este intervalo."""
    query = (
        select(HorarioAula, ProfessorTurmaDisciplina)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == HorarioAula.alocacao_id)
        .where(
            HorarioAula.tenant_id == tenant_id,
            HorarioAula.dia_semana == dia_semana,
            HorarioAula.hora_inicio < hora_fim,
            HorarioAula.hora_fim > hora_inicio,
        )
    )
    if ignorar_horario_id:
        query = query.where(HorarioAula.id != ignorar_horario_id)

    conflitos = (await db.execute(query)).all()
    for horario_existente, alocacao_existente in conflitos:
        if alocacao_existente.turma_id == alocacao.turma_id:
            raise HTTPException(
                status_code=400,
                detail=f"Conflito de horário: esta turma já tem uma aula marcada entre "
                       f"{horario_existente.hora_inicio.strftime('%H:%M')} e {horario_existente.hora_fim.strftime('%H:%M')} nesse dia."
            )
        if alocacao_existente.professor_id == alocacao.professor_id:
            raise HTTPException(
                status_code=400,
                detail=f"Conflito de horário: este professor já tem outra aula marcada entre "
                       f"{horario_existente.hora_inicio.strftime('%H:%M')} e {horario_existente.hora_fim.strftime('%H:%M')} nesse dia."
            )


def _serializar(horario: HorarioAula, alocacao: ProfessorTurmaDisciplina, nome_turma: str, nome_disciplina: str, nome_professor: str) -> dict:
    return {
        "id": horario.id,
        "alocacao_id": horario.alocacao_id,
        "dia_semana": horario.dia_semana,
        "hora_inicio": horario.hora_inicio,
        "hora_fim": horario.hora_fim,
        "sala": horario.sala,
        "turma_id": alocacao.turma_id,
        "nome_turma": nome_turma,
        "disciplina_id": alocacao.disciplina_id,
        "nome_disciplina": nome_disciplina,
        "professor_id": alocacao.professor_id,
        "nome_professor": nome_professor,
    }


def _query_base_grade(tenant_id):
    return (
        select(HorarioAula, ProfessorTurmaDisciplina, Turma.nome_codigo, Disciplina.nome, Usuario.nome_completo)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == HorarioAula.alocacao_id)
        .join(Turma, Turma.id == ProfessorTurmaDisciplina.turma_id)
        .join(Disciplina, Disciplina.id == ProfessorTurmaDisciplina.disciplina_id)
        .join(Professor, Professor.id == ProfessorTurmaDisciplina.professor_id)
        .join(Usuario, Usuario.id == Professor.usuario_id)
        .where(HorarioAula.tenant_id == tenant_id)
        .order_by(HorarioAula.dia_semana, HorarioAula.hora_inicio)
    )


async def listar_grade_da_turma(db: AsyncSession, tenant_id, turma_id: uuid.UUID) -> list[dict]:
    query = _query_base_grade(tenant_id).where(ProfessorTurmaDisciplina.turma_id == turma_id)
    resultado = await db.execute(query)
    return [_serializar(h, a, nt, nd, np) for h, a, nt, nd, np in resultado.all()]


async def listar_grade_do_professor(db: AsyncSession, tenant_id, professor_id: uuid.UUID) -> list[dict]:
    query = _query_base_grade(tenant_id).where(ProfessorTurmaDisciplina.professor_id == professor_id)
    resultado = await db.execute(query)
    return [_serializar(h, a, nt, nd, np) for h, a, nt, nd, np in resultado.all()]


async def listar_minha_grade(db: AsyncSession, utilizador: dict) -> list[dict]:
    """Grade horária do professor autenticado."""
    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor:
        return []
    return await listar_grade_do_professor(db, utilizador["tenant_id"], professor.id)


async def criar_horario(db: AsyncSession, tenant_id, dados: HorarioAulaCreate) -> HorarioAula:
    alocacao = await _obter_alocacao(db, tenant_id, dados.alocacao_id)
    await _validar_sem_conflito(db, tenant_id, alocacao, dados.dia_semana, dados.hora_inicio, dados.hora_fim)

    novo_horario = HorarioAula(
        tenant_id=tenant_id,
        alocacao_id=dados.alocacao_id,
        dia_semana=dados.dia_semana,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
        sala=dados.sala,
    )
    db.add(novo_horario)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Já existe exatamente este slot na grade horária.")
    await db.refresh(novo_horario)
    return novo_horario


async def atualizar_horario(db: AsyncSession, tenant_id, horario_id: uuid.UUID, dados: HorarioAulaUpdate) -> HorarioAula:
    horario = (await db.execute(
        select(HorarioAula).where(HorarioAula.id == horario_id, HorarioAula.tenant_id == tenant_id)
    )).scalars().first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado na sua instituição.")

    alocacao = await _obter_alocacao(db, tenant_id, horario.alocacao_id)

    novo_dia = dados.dia_semana if dados.dia_semana is not None else horario.dia_semana
    nova_hora_inicio = dados.hora_inicio if dados.hora_inicio is not None else horario.hora_inicio
    nova_hora_fim = dados.hora_fim if dados.hora_fim is not None else horario.hora_fim
    if nova_hora_fim <= nova_hora_inicio:
        raise HTTPException(status_code=400, detail="hora_fim tem de ser depois de hora_inicio.")

    await _validar_sem_conflito(db, tenant_id, alocacao, novo_dia, nova_hora_inicio, nova_hora_fim, ignorar_horario_id=horario_id)

    horario.dia_semana = novo_dia
    horario.hora_inicio = nova_hora_inicio
    horario.hora_fim = nova_hora_fim
    if dados.sala is not None:
        horario.sala = dados.sala
    await db.commit()
    await db.refresh(horario)
    return horario


async def remover_horario(db: AsyncSession, tenant_id, horario_id: uuid.UUID) -> None:
    horario = (await db.execute(
        select(HorarioAula).where(HorarioAula.id == horario_id, HorarioAula.tenant_id == tenant_id)
    )).scalars().first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado na sua instituição.")
    await db.delete(horario)
    await db.commit()
