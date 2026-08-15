"""
Configurações da escola (IBAN, moeda, contacto, endereço) — ver
app/database/models.py::Tenant para os campos e app/api/v1/configuracoes.py
para a distinção de acesso (leitura aberta a qualquer autenticado do
tenant, escrita restrita ao GESTOR).
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant
from app.schemas.configuracoes import ConfiguracaoTenantUpdate


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
    await db.commit()
    await db.refresh(tenant)
    return tenant
