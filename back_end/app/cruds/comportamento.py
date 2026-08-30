"""Acesso a dados e regras de negócio dos Registos de Comportamento —
ver app/database/models_diario.py::RegistroComportamento.

Mesmo módulo comercial e a mesma autoria do Diário de Classe (ver
app/cruds/diario.py) — só que aqui um comportamento não está preso a
uma disciplina específica (por isso a validação de autoria do
Professor é só por turma, não por turma+disciplina)."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.models import Usuario
from app.database.models_academico import Disciplina, Turma
from app.database.models_diario import ProfessorTurmaDisciplina, RegistroComportamento
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Professor
from app.schemas.comportamento import RegistroComportamentoCreate

TIPOS_VALIDOS = {"POSITIVO", "NEGATIVO"}


async def _validar_autoria_turma(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID) -> None:
    """Gestor/Secretaria têm acesso administrativo a qualquer turma. Um
    Professor só pode registar/consultar comportamento das turmas onde
    lecciona alguma disciplina (não precisa de ser a disciplina em
    concreto do incidente — um professor pode observar comportamento
    fora da sua própria aula)."""
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return
    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para aceder a Comportamento.")

    professor = (await db.execute(
        select(Professor).where(Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == utilizador["tenant_id"])
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=403, detail="Utilizador não corresponde a nenhum professor cadastrado.")

    alocado = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.professor_id == professor.id, ProfessorTurmaDisciplina.turma_id == turma_id
        )
    )).scalars().first()
    if not alocado:
        raise HTTPException(status_code=403, detail="Só pode aceder a turmas onde lecciona.")


async def _obter_matricula_na_turma(db: AsyncSession, tenant_id, turma_id: uuid.UUID, aluno_id: uuid.UUID) -> Matricula:
    matricula = (await db.execute(
        select(Matricula).where(Matricula.turma_id == turma_id, Matricula.aluno_id == aluno_id, Matricula.tenant_id == tenant_id)
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Aluno não está matriculado nesta turma.")
    return matricula


def _serializar(registo: RegistroComportamento, nome_autor: str | None) -> dict:
    return {
        "id": registo.id,
        "tipo": registo.tipo,
        "descricao": registo.descricao,
        "data_ocorrencia": registo.data_ocorrencia,
        "disciplina_id": registo.disciplina_id,
        "registrado_por_nome": nome_autor or "—",
        "data_criacao": registo.data_criacao,
    }


async def registar_comportamento(
    db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, aluno_id: uuid.UUID, dados: RegistroComportamentoCreate
) -> dict:
    tenant_id = utilizador["tenant_id"]
    if dados.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use um de: {', '.join(sorted(TIPOS_VALIDOS))}.")
    if not dados.descricao.strip():
        raise HTTPException(status_code=400, detail="Descreva o comportamento observado.")

    turma = (await db.execute(select(Turma).where(Turma.id == turma_id, Turma.tenant_id == tenant_id))).scalars().first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")
    await _validar_autoria_turma(db, utilizador, turma_id)

    if dados.disciplina_id:
        disciplina = (await db.execute(
            select(Disciplina).where(Disciplina.id == dados.disciplina_id, Disciplina.tenant_id == tenant_id)
        )).scalars().first()
        if not disciplina:
            raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")

    matricula = await _obter_matricula_na_turma(db, tenant_id, turma_id, aluno_id)

    novo = RegistroComportamento(
        tenant_id=tenant_id, matricula_id=matricula.id, disciplina_id=dados.disciplina_id,
        registrado_por_usuario_id=utilizador["usuario_id"], tipo=dados.tipo,
        descricao=dados.descricao.strip(), data_ocorrencia=dados.data_ocorrencia or date.today(),
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)

    autor = (await db.execute(select(Usuario.nome_completo).where(Usuario.id == utilizador["usuario_id"]))).scalar_one_or_none()
    return _serializar(novo, autor)


async def listar_comportamento_da_turma_aluno(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, aluno_id: uuid.UUID) -> list[dict]:
    tenant_id = utilizador["tenant_id"]
    await _validar_autoria_turma(db, utilizador, turma_id)
    matricula = await _obter_matricula_na_turma(db, tenant_id, turma_id, aluno_id)

    linhas = (await db.execute(
        select(RegistroComportamento, Usuario.nome_completo)
        .outerjoin(Usuario, Usuario.id == RegistroComportamento.registrado_por_usuario_id)
        .where(RegistroComportamento.matricula_id == matricula.id, RegistroComportamento.tenant_id == tenant_id)
        .order_by(RegistroComportamento.data_ocorrencia.desc(), RegistroComportamento.data_criacao.desc())
    )).all()
    return [_serializar(r, nome) for r, nome in linhas]


async def remover_comportamento(db: AsyncSession, utilizador: dict, registo_id: uuid.UUID) -> None:
    tenant_id = utilizador["tenant_id"]
    registo = (await db.execute(
        select(RegistroComportamento).where(RegistroComportamento.id == registo_id, RegistroComportamento.tenant_id == tenant_id)
    )).scalars().first()
    if not registo:
        raise HTTPException(status_code=404, detail="Registo de comportamento não encontrado na sua instituição.")

    matricula = (await db.execute(select(Matricula).where(Matricula.id == registo.matricula_id))).scalars().first()
    if matricula:
        await _validar_autoria_turma(db, utilizador, matricula.turma_id)

    # Um Professor só apaga os seus próprios registos — mesmo com acesso
    # à turma, corrigir/apagar a avaliação de comportamento de outro
    # colega não devia ser possível sem ser Gestor/Secretaria.
    if utilizador["perfil_acesso"] == "PROFESSOR" and registo.registrado_por_usuario_id != utilizador["usuario_id"]:
        raise HTTPException(status_code=403, detail="Só pode remover os registos que você próprio criou.")

    await db.delete(registo)
    await db.commit()


# ==========================================
# PORTAL DO ALUNO/RESPONSÁVEL (resumo — ver cruds/portal.py)
# ==========================================
async def obter_resumo_comportamento_da_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID) -> dict:
    linhas = (await db.execute(
        select(RegistroComportamento, Usuario.nome_completo)
        .outerjoin(Usuario, Usuario.id == RegistroComportamento.registrado_por_usuario_id)
        .where(RegistroComportamento.matricula_id == matricula_id, RegistroComportamento.tenant_id == tenant_id)
        .order_by(RegistroComportamento.data_ocorrencia.desc(), RegistroComportamento.data_criacao.desc())
    )).all()
    positivos = sum(1 for r, _ in linhas if r.tipo == "POSITIVO")
    negativos = sum(1 for r, _ in linhas if r.tipo == "NEGATIVO")
    return {
        "total_positivos": positivos,
        "total_negativos": negativos,
        "recentes": [_serializar(r, nome) for r, nome in linhas[:5]],
    }
