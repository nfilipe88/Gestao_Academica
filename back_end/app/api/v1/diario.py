from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
import uuid

from app.database.session import obter_sessao_db
from app.database.models_academico import Disciplina, Turma
from app.database.models_pessoas import Aluno, Professor
from app.database.models_matricula import Matricula
from app.database.models_diario import (
    PeriodoAvaliacao, ProfessorTurmaDisciplina, RegistroFrequencia, RegistroNota, RegistroNotaAuditoria
)
from app.core.security import obter_utilizador_atual, exigir_perfil

router = APIRouter(prefix="/api/v1/diario", tags=["Diário de Classe"])

NOTA_MINIMA = Decimal("0.0")
NOTA_MAXIMA = Decimal("10.0")

# Só Gestor/Secretaria trancam/reabrem períodos de avaliação — lançar
# notas continua aberto a Professores alocados (_validar_autoria).
_PODE_GERIR_PERIODOS = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# VALIDAÇÕES PARTILHADAS
# ==========================================
async def _validar_turma_disciplina(db: AsyncSession, tenant_id, turma_id: uuid.UUID, disciplina_id: uuid.UUID):
    turma = (await db.execute(
        select(Turma).where(Turma.id == turma_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")


async def _validar_autoria(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID):
    """
    RN01 - Validação de Autoria: Gestor/Secretaria têm acesso administrativo
    a qualquer turma. Um Professor só pode lançar/consultar o diário das
    turmas+disciplinas às quais está efetivamente alocado.
    """
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return

    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para aceder ao Diário de Classe.")

    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"],
            Professor.tenant_id == utilizador["tenant_id"]
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


async def _validar_periodo_aberto(db: AsyncSession, tenant_id, nome_periodo: str):
    """
    RN03 - Janela de Lançamento: só bloqueia se a secretaria tiver
    criado (e trancado) um registo para este nome de período. Um nome
    sem registo correspondente continua livre — a gestão de períodos é
    opcional, não um pré-requisito para lançar notas.
    """
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id, PeriodoAvaliacao.nome == nome_periodo)
    )).scalars().first()
    if periodo and not periodo.aberto:
        raise HTTPException(
            status_code=403,
            detail=f"O período de avaliação \"{nome_periodo}\" está trancado pela secretaria — já não é possível lançar/alterar notas."
        )

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class FrequenciaAluno(BaseModel):
    matricula_id: uuid.UUID
    presenca: bool
    faltas: int = 0

class FrequenciaLoteCreate(BaseModel):
    data_aula: date
    quantidade_aulas: int = 1
    conteudo_programado: str | None = None
    frequencias: list[FrequenciaAluno]

class NotaAluno(BaseModel):
    matricula_id: uuid.UUID
    valor_nota: Decimal

class NotaLoteCreate(BaseModel):
    periodo_avaliacao: str
    tipo_avaliacao: str | None = None
    data_avaliacao: date | None = None
    notas: list[NotaAluno]

class PeriodoAvaliacaoCreate(BaseModel):
    nome: str

# ==========================================
# A. CARREGAR A GRADE (Lista de Alunos da Turma)
# ==========================================
@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}/alunos")
async def listar_alunos_da_turma_disciplina(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os alunos matriculados (ATIVO) para montar a tabela de chamada/notas."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    resultado = await db.execute(
        select(Matricula.id, Aluno.nome_completo, Aluno.matricula_interna)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(
            Matricula.turma_id == turma_id,
            Matricula.status_matricula == "ATIVO",
            Matricula.tenant_id == tenant_id
        )
        .order_by(Aluno.nome_completo)
    )
    return [
        {
            "matricula_id": matricula_id,
            "nome_aluno": nome_aluno,
            "matricula_interna": matricula_interna,
            "numero_chamada": indice + 1,
        }
        for indice, (matricula_id, nome_aluno, matricula_interna) in enumerate(resultado.all())
    ]

# ==========================================
# B. LANÇAMENTO DE FREQUÊNCIA EM LOTE (Chamada)
# ==========================================
@router.post("/turmas/{turma_id}/disciplinas/{disciplina_id}/frequencias/lote", status_code=status.HTTP_201_CREATED)
async def lancar_frequencias_lote(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    dados: FrequenciaLoteCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Recebe a presença/faltas de toda a turma para uma aula, numa única chamada."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    matriculas_da_turma = set((await db.execute(
        select(Matricula.id).where(Matricula.turma_id == turma_id, Matricula.tenant_id == tenant_id)
    )).scalars().all())

    total = 0
    for item in dados.frequencias:
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = (await db.execute(
            select(RegistroFrequencia).where(
                RegistroFrequencia.matricula_id == item.matricula_id,
                RegistroFrequencia.disciplina_id == disciplina_id,
                RegistroFrequencia.data_aula == dados.data_aula
            )
        )).scalars().first()

        if existente:
            # Upsert: relançar a chamada do mesmo dia atualiza, não duplica.
            existente.presenca = item.presenca
            existente.faltas = item.faltas
            existente.quantidade_aulas = dados.quantidade_aulas
            existente.conteudo_programado = dados.conteudo_programado
        else:
            db.add(RegistroFrequencia(
                tenant_id=tenant_id,
                matricula_id=item.matricula_id,
                disciplina_id=disciplina_id,
                data_aula=dados.data_aula,
                quantidade_aulas=dados.quantidade_aulas,
                conteudo_programado=dados.conteudo_programado,
                presenca=item.presenca,
                faltas=item.faltas
            ))
        total += 1

    await db.commit()
    return {"mensagem": "Frequência registada com sucesso", "total": total}

# ==========================================
# C. LANÇAMENTO DE NOTAS EM LOTE
# ==========================================
@router.post("/turmas/{turma_id}/disciplinas/{disciplina_id}/notas/lote")
async def lancar_notas_lote(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    dados: NotaLoteCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """
    Upsert das notas de toda a turma para um período de avaliação.
    RN02: valor_nota tem de estar entre 0.0 e 10.0.
    RN04: se a nota já existia e o valor mudou, fica um registo de auditoria.
    """
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, dados.periodo_avaliacao)

    matriculas_da_turma = set((await db.execute(
        select(Matricula.id).where(Matricula.turma_id == turma_id, Matricula.tenant_id == tenant_id)
    )).scalars().all())

    total = 0
    for item in dados.notas:
        if item.valor_nota < NOTA_MINIMA or item.valor_nota > NOTA_MAXIMA:
            raise HTTPException(
                status_code=400,
                detail=f"Nota {item.valor_nota} fora do intervalo permitido ({NOTA_MINIMA} a {NOTA_MAXIMA})."
            )
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = (await db.execute(
            select(RegistroNota).where(
                RegistroNota.matricula_id == item.matricula_id,
                RegistroNota.disciplina_id == disciplina_id,
                RegistroNota.periodo_avaliacao == dados.periodo_avaliacao
            )
        )).scalars().first()

        if existente:
            if existente.valor_nota != item.valor_nota:
                # RN04 - Auditoria: só regista quando o valor realmente muda.
                db.add(RegistroNotaAuditoria(
                    tenant_id=tenant_id,
                    registro_nota_id=existente.id,
                    alterado_por=utilizador["usuario_id"],
                    valor_antigo=existente.valor_nota,
                    valor_novo=item.valor_nota
                ))
                existente.valor_nota = item.valor_nota
            existente.tipo_avaliacao = dados.tipo_avaliacao
            existente.data_avaliacao = dados.data_avaliacao
        else:
            db.add(RegistroNota(
                tenant_id=tenant_id,
                matricula_id=item.matricula_id,
                disciplina_id=disciplina_id,
                periodo_avaliacao=dados.periodo_avaliacao,
                tipo_avaliacao=dados.tipo_avaliacao,
                data_avaliacao=dados.data_avaliacao,
                valor_nota=item.valor_nota
            ))
        total += 1

    await db.commit()
    return {"mensagem": "Notas registadas com sucesso", "total": total}

# ==========================================
# D. VISÃO GERAL DO DESEMPENHO (Dashboard do Professor)
# ==========================================
@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}/consolidado")
async def consolidado_turma_disciplina(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    periodo_avaliacao: str | None = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Média da turma, alunos abaixo da média e total de faltas — para o professor bater o olho antes do conselho de turma."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    matriculas_ids = (await db.execute(
        select(Matricula.id).where(
            Matricula.turma_id == turma_id,
            Matricula.status_matricula == "ATIVO",
            Matricula.tenant_id == tenant_id
        )
    )).scalars().all()

    query_notas = select(RegistroNota.valor_nota).where(
        RegistroNota.disciplina_id == disciplina_id,
        RegistroNota.matricula_id.in_(matriculas_ids)
    )
    if periodo_avaliacao:
        query_notas = query_notas.where(RegistroNota.periodo_avaliacao == periodo_avaliacao)
    notas = (await db.execute(query_notas)).scalars().all()

    if notas:
        media_turma = sum(notas) / len(notas)
        alunos_abaixo_da_media = sum(1 for nota in notas if nota < media_turma)
    else:
        media_turma = None
        alunos_abaixo_da_media = 0

    total_faltas = (await db.execute(
        select(func.coalesce(func.sum(RegistroFrequencia.faltas), 0)).where(
            RegistroFrequencia.disciplina_id == disciplina_id,
            RegistroFrequencia.matricula_id.in_(matriculas_ids)
        )
    )).scalar_one()

    return {
        "total_alunos": len(matriculas_ids),
        "media_turma": float(media_turma) if media_turma is not None else None,
        "alunos_abaixo_da_media": alunos_abaixo_da_media,
        "total_faltas": int(total_faltas),
    }

# ==========================================
# E. PERÍODOS DE AVALIAÇÃO (RN03 — Janela de Lançamento)
# ==========================================
@router.get("/periodos")
async def listar_periodos_avaliacao(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os períodos geridos pela secretaria (abertos e trancados). Leitura aberta a qualquer utilizador autenticado — o Professor precisa de ver o que está trancado."""
    periodos = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == utilizador["tenant_id"])
        .order_by(PeriodoAvaliacao.data_criacao)
    )).scalars().all()
    return periodos


@router.post("/periodos", status_code=status.HTTP_201_CREATED)
async def criar_periodo_avaliacao(
    dados: PeriodoAvaliacaoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR_PERIODOS)
):
    """Regista um período (ex: "1º Bimestre") como geríve — nasce aberto; usar /trancar quando o prazo terminar."""
    novo_periodo = PeriodoAvaliacao(tenant_id=utilizador["tenant_id"], nome=dados.nome, aberto=True)
    db.add(novo_periodo)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um período de avaliação com este nome.")
    await db.refresh(novo_periodo)
    return novo_periodo


@router.patch("/periodos/{periodo_id}/trancar")
async def trancar_periodo_avaliacao(
    periodo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR_PERIODOS)
):
    """A partir de agora, POST .../notas/lote com este periodo_avaliacao devolve 403."""
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.id == periodo_id, PeriodoAvaliacao.tenant_id == utilizador["tenant_id"])
    )).scalars().first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período de avaliação não encontrado na sua instituição.")

    periodo.aberto = False
    periodo.data_fecho = date.today()
    await db.commit()
    return {"mensagem": f'Período "{periodo.nome}" trancado com sucesso.'}


@router.patch("/periodos/{periodo_id}/reabrir")
async def reabrir_periodo_avaliacao(
    periodo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR_PERIODOS)
):
    """Corrige um trancamento feito por engano — volta a permitir lançamentos."""
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.id == periodo_id, PeriodoAvaliacao.tenant_id == utilizador["tenant_id"])
    )).scalars().first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período de avaliação não encontrado na sua instituição.")

    periodo.aberto = True
    periodo.data_fecho = None
    await db.commit()
    return {"mensagem": f'Período "{periodo.nome}" reaberto com sucesso.'}
