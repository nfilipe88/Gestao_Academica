"""
Configurações da escola (IBAN, moeda, contacto, endereço, nota mínima
de aprovação e catálogo de tipos de avaliação) — ver
app/database/models.py::Tenant e app/database/models_diario.py::TipoAvaliacaoConfig
para os campos, e app/api/v1/configuracoes.py para a distinção de
acesso (leitura aberta a qualquer autenticado do tenant, escrita
restrita ao GESTOR).
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant
from app.database.models_diario import Avaliacao, TipoAvaliacaoConfig
from app.schemas.configuracoes import ConfiguracaoTenantUpdate, TipoAvaliacaoCreate, TipoAvaliacaoUpdate


async def _obter_tenant(db: AsyncSession, tenant_id) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    return tenant


async def obter_configuracao(db: AsyncSession, tenant_id) -> Tenant:
    return await _obter_tenant(db, tenant_id)


async def atualizar_configuracao(db: AsyncSession, tenant_id, dados: ConfiguracaoTenantUpdate) -> Tenant:
    tenant = await _obter_tenant(db, tenant_id)
    tenant.iban = dados.iban
    tenant.moeda = dados.moeda
    tenant.telefone_contacto = dados.telefone_contacto
    tenant.email_contacto = dados.email_contacto
    tenant.morada = dados.morada
    tenant.cidade = dados.cidade
    tenant.codigo_postal = dados.codigo_postal
    tenant.pais = dados.pais
    tenant.nota_minima_aprovacao = dados.nota_minima_aprovacao
    tenant.periodo_manha_inicio = dados.periodo_manha_inicio
    tenant.periodo_manha_fim = dados.periodo_manha_fim
    tenant.periodo_tarde_inicio = dados.periodo_tarde_inicio
    tenant.periodo_tarde_fim = dados.periodo_tarde_fim
    tenant.periodo_pos_laboral_inicio = dados.periodo_pos_laboral_inicio
    tenant.periodo_pos_laboral_fim = dados.periodo_pos_laboral_fim
    await db.commit()
    await db.refresh(tenant)
    return tenant


# ==========================================
# TIPOS DE AVALIAÇÃO (catálogo por escola)
# ==========================================
async def listar_tipos_avaliacao(db: AsyncSession, tenant_id) -> list[TipoAvaliacaoConfig]:
    return (await db.execute(
        select(TipoAvaliacaoConfig).where(TipoAvaliacaoConfig.tenant_id == tenant_id).order_by(TipoAvaliacaoConfig.nome)
    )).scalars().all()


async def criar_tipo_avaliacao(db: AsyncSession, tenant_id, dados: TipoAvaliacaoCreate) -> TipoAvaliacaoConfig:
    nome = dados.nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="O nome do tipo de avaliação não pode ficar vazio.")
    existente = (await db.execute(
        select(TipoAvaliacaoConfig).where(TipoAvaliacaoConfig.tenant_id == tenant_id, TipoAvaliacaoConfig.nome == nome)
    )).scalars().first()
    if existente:
        raise HTTPException(status_code=400, detail=f'Já existe um tipo de avaliação chamado "{nome}".')

    novo = TipoAvaliacaoConfig(tenant_id=tenant_id, nome=nome, requer_agendamento=dados.requer_agendamento, ativo=True)
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return novo


async def atualizar_tipo_avaliacao(db: AsyncSession, tenant_id, tipo_id: uuid.UUID, dados: TipoAvaliacaoUpdate) -> TipoAvaliacaoConfig:
    tipo = (await db.execute(
        select(TipoAvaliacaoConfig).where(TipoAvaliacaoConfig.id == tipo_id, TipoAvaliacaoConfig.tenant_id == tenant_id)
    )).scalars().first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de avaliação não encontrado na sua instituição.")

    nome_novo = dados.nome.strip()
    if not nome_novo:
        raise HTTPException(status_code=400, detail="O nome do tipo de avaliação não pode ficar vazio.")
    if nome_novo != tipo.nome:
        # Renomear quebra a ligação com Avaliacao já criadas com o nome
        # antigo (tipo_avaliacao é guardado como texto lá, não FK — ver
        # docstring de TipoAvaliacaoConfig) — avisa em vez de impedir,
        # já que a pior consequência é essas avaliações antigas
        # deixarem de exigir agendamento (falha aberta, não fechada).
        ja_usado = (await db.execute(
            select(Avaliacao.id).where(Avaliacao.tenant_id == tenant_id, Avaliacao.tipo_avaliacao == tipo.nome).limit(1)
        )).first()
        if ja_usado:
            raise HTTPException(
                status_code=400,
                detail=f'Não é possível renomear "{tipo.nome}" — já há avaliações criadas com este tipo. '
                       f"Desative-o e crie um tipo novo em vez de o renomear."
            )
        existente = (await db.execute(
            select(TipoAvaliacaoConfig).where(TipoAvaliacaoConfig.tenant_id == tenant_id, TipoAvaliacaoConfig.nome == nome_novo)
        )).scalars().first()
        if existente:
            raise HTTPException(status_code=400, detail=f'Já existe um tipo de avaliação chamado "{nome_novo}".')

    tipo.nome = nome_novo
    tipo.requer_agendamento = dados.requer_agendamento
    tipo.ativo = dados.ativo
    await db.commit()
    await db.refresh(tipo)
    return tipo
