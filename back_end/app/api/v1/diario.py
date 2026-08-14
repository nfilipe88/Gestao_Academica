from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.schemas.diario import FrequenciaLoteCreate, NotaLoteCreate, PeriodoAvaliacaoCreate
from app.cruds import diario as crud_diario

router = APIRouter(prefix="/api/v1/diario", tags=["Diário de Classe"])

# Só Gestor/Secretaria trancam/reabrem períodos de avaliação — lançar
# notas continua aberto a Professores alocados (validado no crud).
_PODE_GERIR_PERIODOS = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# A. CARREGAR A GRADE (Lista de Alunos da Turma)
# ==========================================
@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}/alunos")
async def listar_alunos_da_turma_disciplina(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os alunos matriculados (ATIVO) para montar a tabela de chamada/notas."""
    return await crud_diario.listar_alunos_da_turma_disciplina(db, utilizador, turma_id, disciplina_id)

# ==========================================
# B. LANÇAMENTO DE FREQUÊNCIA EM LOTE (Chamada)
# ==========================================
@router.post("/turmas/{turma_id}/disciplinas/{disciplina_id}/frequencias/lote", status_code=status.HTTP_201_CREATED)
async def lancar_frequencias_lote(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    dados: FrequenciaLoteCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Recebe a presença/faltas de toda a turma para uma aula, numa única chamada."""
    total = await crud_diario.lancar_frequencias_lote(db, utilizador, turma_id, disciplina_id, dados)
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
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Upsert das notas de toda a turma para um período de avaliação (RN02/RN03/RN04)."""
    total = await crud_diario.lancar_notas_lote(db, utilizador, turma_id, disciplina_id, dados)
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
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Média da turma, alunos abaixo da média e total de faltas — para o professor bater o olho antes do conselho de turma."""
    return await crud_diario.consolidado_turma_disciplina(db, utilizador, turma_id, disciplina_id, periodo_avaliacao)

# ==========================================
# E. PERÍODOS DE AVALIAÇÃO (RN03 — Janela de Lançamento)
# ==========================================
@router.get("/periodos")
async def listar_periodos_avaliacao(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os períodos geridos pela secretaria (abertos e trancados). Leitura aberta a qualquer funcionário da escola — o Professor precisa de ver o que está trancado."""
    return await crud_diario.listar_periodos_avaliacao(db, utilizador["tenant_id"])

@router.post("/periodos", status_code=status.HTTP_201_CREATED)
async def criar_periodo_avaliacao(
    dados: PeriodoAvaliacaoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR_PERIODOS)
):
    """Regista um período (ex: "1º Bimestre") como gerível — nasce aberto; usar /trancar quando o prazo terminar."""
    return await crud_diario.criar_periodo_avaliacao(db, utilizador["tenant_id"], dados)

@router.patch("/periodos/{periodo_id}/trancar")
async def trancar_periodo_avaliacao(
    periodo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR_PERIODOS)
):
    """A partir de agora, POST .../notas/lote com este periodo_avaliacao devolve 403."""
    periodo = await crud_diario.trancar_periodo_avaliacao(db, utilizador["tenant_id"], periodo_id)
    return {"mensagem": f'Período "{periodo.nome}" trancado com sucesso.'}

@router.patch("/periodos/{periodo_id}/reabrir")
async def reabrir_periodo_avaliacao(
    periodo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR_PERIODOS)
):
    """Corrige um trancamento feito por engano — volta a permitir lançamentos."""
    periodo = await crud_diario.reabrir_periodo_avaliacao(db, utilizador["tenant_id"], periodo_id)
    return {"mensagem": f'Período "{periodo.nome}" reaberto com sucesso.'}
