import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db, obter_sessao_db_publica
from app.core.security import obter_utilizador_atual, exigir_perfil
from app.schemas.crm import EtapaCreate, LeadPublicoCreate, LeadStaffCreate, LeadUpdate, OportunidadeCreate, OportunidadeMover
from app.cruds import crm as crud_crm

router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])
router_publico = APIRouter(prefix="/api/v1/public", tags=["Público"])

# O CRM é back-office puro (dados de contacto de famílias ainda não
# matriculadas) — Professor não precisa disto, ao contrário do
# Financeiro/Diário onde a leitura fica aberta.
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

# ==========================================
# A. CAPTAÇÃO PÚBLICA (RN03) — sem autenticação
# ==========================================
@router_publico.post("/{tenant_id}/leads", status_code=status.HTTP_201_CREATED)
async def criar_lead_publico(
    tenant_id: uuid.UUID,
    dados: LeadPublicoCreate,
    db: AsyncSession = Depends(obter_sessao_db_publica)
):
    """Endpoint público para a escola incorporar um formulário no seu próprio site (RN03)."""
    await crud_crm.criar_lead_publico(db, tenant_id, dados)
    return {"mensagem": "Pedido de contacto recebido com sucesso! Entraremos em contacto brevemente."}

# ==========================================
# B. FUNIL (Kanban)
# ==========================================
@router.get("/funil")
async def listar_funil(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    return await crud_crm.listar_funil(db, utilizador["tenant_id"])

@router.post("/etapas", status_code=status.HTTP_201_CREATED)
async def criar_etapa(
    dados: EtapaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    return await crud_crm.criar_etapa(db, utilizador["tenant_id"], dados)

# ==========================================
# C. LEADS
# ==========================================
@router.get("/leads")
async def listar_leads(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    return await crud_crm.listar_leads(db, utilizador["tenant_id"])

@router.post("/leads", status_code=status.HTTP_201_CREATED)
async def criar_lead_manual(
    dados: LeadStaffCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Regista um Lead diretamente pela Secretaria (ex: telefonema, visita) e já o coloca na 1ª etapa do funil."""
    lead, oportunidade_id = await crud_crm.criar_lead_manual(db, utilizador["tenant_id"], dados)
    return {"lead": lead, "oportunidade_id": oportunidade_id}

@router.patch("/leads/{lead_id}")
async def atualizar_lead(
    lead_id: uuid.UUID,
    dados: LeadUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Completa/corrige os dados do Lead — em particular a data de nascimento, exigida antes da conversão (RN01)."""
    return await crud_crm.atualizar_lead(db, utilizador["tenant_id"], lead_id, dados)

# ==========================================
# D. OPORTUNIDADES
# ==========================================
@router.get("/oportunidades")
async def listar_oportunidades(
    etapa_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Lista as oportunidades já com os dados do Lead, para montar o quadro Kanban."""
    return await crud_crm.listar_oportunidades(db, utilizador["tenant_id"], etapa_id)

@router.post("/oportunidades", status_code=status.HTTP_201_CREATED)
async def criar_oportunidade(
    dados: OportunidadeCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria manualmente uma oportunidade para um Lead já existente (ex: contacto presencial), na 1ª etapa do funil."""
    return await crud_crm.criar_oportunidade(db, utilizador["tenant_id"], dados)

@router.patch("/oportunidades/{oportunidade_id}/mover")
async def mover_oportunidade(
    oportunidade_id: uuid.UUID,
    dados: OportunidadeMover,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Move o cartão para outra etapa. Se a etapa de destino for eh_etapa_ganho, aciona a RN01."""
    oportunidade, mensagem = await crud_crm.mover_oportunidade(db, utilizador["tenant_id"], oportunidade_id, dados.nova_etapa_id)
    return {"mensagem": mensagem, "oportunidade": oportunidade, "aluno_gerado_id": oportunidade.aluno_gerado_id}
