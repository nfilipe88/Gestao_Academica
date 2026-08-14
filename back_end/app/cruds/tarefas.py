"""
Acesso a dados e regras de negócio de Trabalhos/Tarefas.

Distinto do Diário de Classe (RegistroNota): uma Tarefa tem prazo de
entrega e uma avaliação por aluno com status de entrega (não só um
valor), mas reutiliza as mesmas regras de autoria e de período
trancado já estabelecidas em cruds/diario.py.

RN01 - Autoria: só o professor alocado (ou Gestor/Secretaria) cria
tarefas e avalia entregas.
RN02 - Nota entre 0 e valor_maximo da tarefa.
RN03 - Período trancado (opcional): se a tarefa tiver periodo_avaliacao
preenchido e esse período estiver trancado, bloqueia a avaliação.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from app.database.models_academico import Disciplina, Turma
from app.database.models_pessoas import Aluno, Professor
from app.database.models_matricula import Matricula
from app.database.models_diario import PeriodoAvaliacao, ProfessorTurmaDisciplina
from app.database.models_tarefas import Tarefa, TarefaAvaliacao
from app.schemas.tarefas import AvaliarTarefaLote, TarefaCreate

STATUS_AVALIACAO_VALIDOS = {"ENTREGUE", "ENTREGUE_ATRASADO", "NAO_ENTREGUE"}


# ==========================================
# VALIDAÇÕES PARTILHADAS (mesmo padrão de cruds/diario.py)
# ==========================================
async def _obter_alocacao(db: AsyncSession, tenant_id, alocacao_id: uuid.UUID) -> ProfessorTurmaDisciplina:
    alocacao = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.id == alocacao_id, ProfessorTurmaDisciplina.tenant_id == tenant_id
        )
    )).scalars().first()
    if not alocacao:
        raise HTTPException(status_code=404, detail="Alocação (Professor/Turma/Disciplina) não encontrada na sua instituição.")
    return alocacao


async def _validar_autoria_alocacao(db: AsyncSession, utilizador: dict, alocacao: ProfessorTurmaDisciplina):
    """RN01: Gestor/Secretaria têm acesso a qualquer turma; Professor só à sua própria alocação."""
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return
    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para aceder a Trabalhos/Tarefas.")

    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor or professor.id != alocacao.professor_id:
        raise HTTPException(status_code=403, detail="Não lecciona esta disciplina nesta turma.")


async def _validar_autoria_turma_disciplina(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID):
    """Mesma RN01, mas a partir de turma_id+disciplina_id — usado na listagem (o mesmo padrão do Diário)."""
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return
    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para aceder a Trabalhos/Tarefas.")

    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=403, detail="Utilizador não corresponde a nenhum professor cadastrado.")

    alocado = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.professor_id == professor.id,
            ProfessorTurmaDisciplina.turma_id == turma_id,
            ProfessorTurmaDisciplina.disciplina_id == disciplina_id
        )
    )).scalars().first()
    if not alocado:
        raise HTTPException(status_code=403, detail="Não lecciona esta disciplina nesta turma.")


async def _validar_periodo_aberto(db: AsyncSession, tenant_id, nome_periodo: str | None):
    """RN03 (opcional, igual ao Diário): só bloqueia se o período existir e estiver trancado."""
    if not nome_periodo:
        return
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id, PeriodoAvaliacao.nome == nome_periodo)
    )).scalars().first()
    if periodo and not periodo.aberto:
        raise HTTPException(
            status_code=403,
            detail=f"O período de avaliação \"{nome_periodo}\" está trancado pela secretaria — já não é possível avaliar este trabalho."
        )


async def _matriculas_ativas_da_turma(db: AsyncSession, tenant_id, turma_id: uuid.UUID) -> list[uuid.UUID]:
    return (await db.execute(
        select(Matricula.id).where(
            Matricula.turma_id == turma_id, Matricula.status_matricula == "ATIVO", Matricula.tenant_id == tenant_id
        )
    )).scalars().all()


async def _garantir_avaliacoes_da_turma(db: AsyncSession, tenant_id, tarefa: Tarefa, turma_id: uuid.UUID):
    """
    Cria a linha PENDENTE para qualquer aluno ATIVO da turma que ainda
    não tenha uma TarefaAvaliacao — cobre tanto a criação da tarefa
    como alunos matriculados depois dela já existir.
    """
    matriculas_ids = await _matriculas_ativas_da_turma(db, tenant_id, turma_id)
    if not matriculas_ids:
        return

    ja_existentes = set((await db.execute(
        select(TarefaAvaliacao.matricula_id).where(TarefaAvaliacao.tarefa_id == tarefa.id)
    )).scalars().all())

    for matricula_id in matriculas_ids:
        if matricula_id not in ja_existentes:
            db.add(TarefaAvaliacao(
                tenant_id=tenant_id, tarefa_id=tarefa.id, matricula_id=matricula_id, status="PENDENTE"
            ))
    await db.commit()


def _serializar_tarefa(tarefa: Tarefa, turma_id, nome_turma: str, disciplina_id, nome_disciplina: str) -> dict:
    return {
        "id": tarefa.id,
        "alocacao_id": tarefa.alocacao_id,
        "titulo": tarefa.titulo,
        "descricao": tarefa.descricao,
        "data_entrega": tarefa.data_entrega,
        "valor_maximo": tarefa.valor_maximo,
        "periodo_avaliacao": tarefa.periodo_avaliacao,
        "data_criacao": tarefa.data_criacao,
        "turma_id": turma_id,
        "nome_turma": nome_turma,
        "disciplina_id": disciplina_id,
        "nome_disciplina": nome_disciplina,
    }


# ==========================================
# A. CRIAR TAREFA
# ==========================================
async def criar_tarefa(db: AsyncSession, utilizador: dict, dados: TarefaCreate) -> dict:
    tenant_id = utilizador["tenant_id"]
    alocacao = await _obter_alocacao(db, tenant_id, dados.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    nova_tarefa = Tarefa(
        tenant_id=tenant_id,
        alocacao_id=dados.alocacao_id,
        titulo=dados.titulo,
        descricao=dados.descricao,
        data_entrega=dados.data_entrega,
        valor_maximo=dados.valor_maximo,
        periodo_avaliacao=dados.periodo_avaliacao,
    )
    db.add(nova_tarefa)
    await db.commit()
    await db.refresh(nova_tarefa)

    await _garantir_avaliacoes_da_turma(db, tenant_id, nova_tarefa, alocacao.turma_id)

    turma = (await db.execute(select(Turma).where(Turma.id == alocacao.turma_id))).scalars().first()
    disciplina = (await db.execute(select(Disciplina).where(Disciplina.id == alocacao.disciplina_id))).scalars().first()
    return _serializar_tarefa(nova_tarefa, alocacao.turma_id, turma.nome_codigo, alocacao.disciplina_id, disciplina.nome)


# ==========================================
# B. LISTAR TAREFAS DE UMA TURMA+DISCIPLINA
# ==========================================
async def listar_tarefas_da_turma_disciplina(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID) -> list[dict]:
    tenant_id = utilizador["tenant_id"]
    await _validar_autoria_turma_disciplina(db, utilizador, turma_id, disciplina_id)

    resultado = await db.execute(
        select(Tarefa, Turma.nome_codigo, Disciplina.nome)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == Tarefa.alocacao_id)
        .join(Turma, Turma.id == ProfessorTurmaDisciplina.turma_id)
        .join(Disciplina, Disciplina.id == ProfessorTurmaDisciplina.disciplina_id)
        .where(
            ProfessorTurmaDisciplina.turma_id == turma_id,
            ProfessorTurmaDisciplina.disciplina_id == disciplina_id,
            Tarefa.tenant_id == tenant_id
        )
        .order_by(Tarefa.data_entrega.desc())
    )
    return [_serializar_tarefa(t, turma_id, nome_turma, disciplina_id, nome_disciplina) for t, nome_turma, nome_disciplina in resultado.all()]


# ==========================================
# C. DETALHE DE UMA TAREFA (com a lista de avaliações, para a UI de correção)
# ==========================================
async def obter_tarefa_com_avaliacoes(db: AsyncSession, utilizador: dict, tarefa_id: uuid.UUID) -> dict:
    tenant_id = utilizador["tenant_id"]
    tarefa = (await db.execute(select(Tarefa).where(Tarefa.id == tarefa_id, Tarefa.tenant_id == tenant_id))).scalars().first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Trabalho/Tarefa não encontrado(a) na sua instituição.")

    alocacao = await _obter_alocacao(db, tenant_id, tarefa.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    # Cobre alunos matriculados depois da tarefa ter sido criada.
    await _garantir_avaliacoes_da_turma(db, tenant_id, tarefa, alocacao.turma_id)

    turma = (await db.execute(select(Turma).where(Turma.id == alocacao.turma_id))).scalars().first()
    disciplina = (await db.execute(select(Disciplina).where(Disciplina.id == alocacao.disciplina_id))).scalars().first()

    linhas = (await db.execute(
        select(TarefaAvaliacao, Aluno.nome_completo, Aluno.matricula_interna)
        .join(Matricula, Matricula.id == TarefaAvaliacao.matricula_id)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(TarefaAvaliacao.tarefa_id == tarefa_id)
        .order_by(Aluno.nome_completo)
    )).all()

    avaliacoes = [
        {
            "id": av.id,
            "matricula_id": av.matricula_id,
            "nome_aluno": nome_aluno,
            "matricula_interna": matricula_interna,
            "status": av.status,
            "nota": av.nota,
            "observacoes": av.observacoes,
            "data_avaliacao": av.data_avaliacao,
        }
        for av, nome_aluno, matricula_interna in linhas
    ]

    tarefa_serializada = _serializar_tarefa(tarefa, alocacao.turma_id, turma.nome_codigo, alocacao.disciplina_id, disciplina.nome)
    tarefa_serializada["avaliacoes"] = avaliacoes
    return tarefa_serializada


# ==========================================
# D. AVALIAR EM LOTE
# ==========================================
async def avaliar_tarefa_lote(db: AsyncSession, utilizador: dict, tarefa_id: uuid.UUID, dados: AvaliarTarefaLote) -> int:
    tenant_id = utilizador["tenant_id"]
    tarefa = (await db.execute(select(Tarefa).where(Tarefa.id == tarefa_id, Tarefa.tenant_id == tenant_id))).scalars().first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Trabalho/Tarefa não encontrado(a) na sua instituição.")

    alocacao = await _obter_alocacao(db, tenant_id, tarefa.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)
    await _validar_periodo_aberto(db, tenant_id, tarefa.periodo_avaliacao)

    matriculas_da_turma = set(await _matriculas_ativas_da_turma(db, tenant_id, alocacao.turma_id))

    total = 0
    for item in dados.avaliacoes:
        if item.status not in STATUS_AVALIACAO_VALIDOS:
            raise HTTPException(status_code=400, detail=f"Status inválido: {item.status}. Use um de: {', '.join(sorted(STATUS_AVALIACAO_VALIDOS))}.")
        if item.nota is not None and (item.nota < 0 or item.nota > tarefa.valor_maximo):
            raise HTTPException(
                status_code=400,
                detail=f"Nota {item.nota} fora do intervalo permitido (0 a {tarefa.valor_maximo})."
            )
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = (await db.execute(
            select(TarefaAvaliacao).where(
                TarefaAvaliacao.tarefa_id == tarefa_id, TarefaAvaliacao.matricula_id == item.matricula_id
            )
        )).scalars().first()

        if existente:
            existente.status = item.status
            existente.nota = item.nota
            existente.observacoes = item.observacoes
            existente.data_avaliacao = datetime.now(timezone.utc)
        else:
            db.add(TarefaAvaliacao(
                tenant_id=tenant_id, tarefa_id=tarefa_id, matricula_id=item.matricula_id,
                status=item.status, nota=item.nota, observacoes=item.observacoes,
                data_avaliacao=datetime.now(timezone.utc)
            ))
        total += 1

    await db.commit()
    return total


# ==========================================
# E. TAREFAS DE UM ALUNO (usado pelo Portal do Aluno/Responsável)
# ==========================================
async def listar_tarefas_do_aluno(db: AsyncSession, tenant_id, matricula_id: uuid.UUID) -> list[dict]:
    resultado = await db.execute(
        select(TarefaAvaliacao, Tarefa, Turma.nome_codigo, Disciplina.nome)
        .join(Tarefa, Tarefa.id == TarefaAvaliacao.tarefa_id)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == Tarefa.alocacao_id)
        .join(Turma, Turma.id == ProfessorTurmaDisciplina.turma_id)
        .join(Disciplina, Disciplina.id == ProfessorTurmaDisciplina.disciplina_id)
        .where(TarefaAvaliacao.matricula_id == matricula_id, TarefaAvaliacao.tenant_id == tenant_id)
        .order_by(Tarefa.data_entrega.desc())
    )
    return [
        {
            "tarefa_id": tarefa.id,
            "titulo": tarefa.titulo,
            "descricao": tarefa.descricao,
            "data_entrega": tarefa.data_entrega,
            "valor_maximo": tarefa.valor_maximo,
            "nome_turma": nome_turma,
            "nome_disciplina": nome_disciplina,
            "status": av.status,
            "nota": av.nota,
            "observacoes": av.observacoes,
        }
        for av, tarefa, nome_turma, nome_disciplina in resultado.all()
    ]
