from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.schemas.diario import (
    AvaliacaoCreate, AvaliacaoUpdate, FrequenciaLoteCreate, NotaAvaliacaoLoteCreate, NotaLoteCreate, PeriodoAvaliacaoCreate
)
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

# ==========================================
# F. AVALIAÇÕES (Provas e Contínuas) + Nota Final Calculada
# ==========================================
@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}/avaliacoes")
async def listar_avaliacoes(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    periodo_avaliacao: str | None = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista as avaliações (provas/contínuas) de uma turma+disciplina, opcionalmente filtradas por período."""
    return await crud_diario.listar_avaliacoes(db, utilizador, turma_id, disciplina_id, periodo_avaliacao)

@router.post("/turmas/{turma_id}/disciplinas/{disciplina_id}/avaliacoes", status_code=status.HTTP_201_CREATED)
async def criar_avaliacao(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    dados: AvaliacaoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Cria uma prova ou avaliação contínua — o Professor precisa de estar alocado a esta turma+disciplina (validado no crud)."""
    return await crud_diario.criar_avaliacao(db, utilizador, turma_id, disciplina_id, dados)

@router.patch("/avaliacoes/{avaliacao_id}")
async def atualizar_avaliacao(
    avaliacao_id: uuid.UUID,
    dados: AvaliacaoUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Edita título/tipo/peso/data — se o peso mudar, a nota final de quem já tinha nota nesta avaliação é recalculada."""
    return await crud_diario.atualizar_avaliacao(db, utilizador, avaliacao_id, dados)

@router.delete("/avaliacoes/{avaliacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_avaliacao(
    avaliacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Apaga a avaliação e as notas lançadas nela — a nota final do período de quem tinha nota aqui é recalculada."""
    await crud_diario.apagar_avaliacao(db, utilizador, avaliacao_id)

@router.get("/avaliacoes/{avaliacao_id}/notas")
async def listar_notas_avaliacao(
    avaliacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Notas já lançadas nesta avaliação — para pré-preencher o formulário ao reabri-la."""
    return await crud_diario.listar_notas_avaliacao(db, utilizador, avaliacao_id)

@router.post("/avaliacoes/{avaliacao_id}/notas/lote")
async def lancar_notas_avaliacao_lote(
    avaliacao_id: uuid.UUID,
    dados: NotaAvaliacaoLoteCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Upsert das notas de toda a turma nesta avaliação — a nota final do período de cada aluno afetado é recalculada."""
    total = await crud_diario.lancar_notas_avaliacao_lote(db, utilizador, avaliacao_id, dados)
    return {"mensagem": "Notas da avaliação registadas com sucesso", "total": total}

@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}/notas-finais")
async def listar_notas_finais(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    periodo_avaliacao: str,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Nota final de cada aluno da turma neste período — calculada a partir das avaliações, ou manual (lançamentos antigos)."""
    return await crud_diario.listar_notas_finais(db, utilizador, turma_id, disciplina_id, periodo_avaliacao)
