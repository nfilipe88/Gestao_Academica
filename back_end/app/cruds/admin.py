"""
Acesso a dados do Painel Super Admin.

Ao contrário de todos os outros módulos, este é intencionalmente
multi-tenant na leitura: nenhuma função aqui filtra por tenant_id — é
o Super Admin quem gere as instituições em si. Só é alcançável através
de exigir_perfil("SUPER_ADMIN") na camada de API (app/api/v1/admin.py).
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_pessoas import Aluno, Professor
from app.schemas.admin import TenantStatusUpdate

STATUS_VALIDOS = {"ATIVO", "SUSPENSO"}

# NIF reservado ao tenant interno da plataforma (onde vivem os logins
# SUPER_ADMIN, criado por seed_super_admin.py) — nunca aparece na lista
# de escolas geridas, nem pode ser suspenso.
NIF_PLATAFORMA = "00000000000"


async def listar_tenants(db: AsyncSession) -> list[dict]:
    """Todas as instituições da plataforma (exceto o tenant interno), com contagens básicas de uso."""
    tenants = (await db.execute(
        select(Tenant).where(Tenant.nif != NIF_PLATAFORMA).order_by(Tenant.data_criacao.desc())
    )).scalars().all()
    if not tenants:
        return []

    tenant_ids = [t.id for t in tenants]

    contagem_usuarios = dict((await db.execute(
        select(Usuario.tenant_id, func.count(Usuario.id))
        .where(Usuario.tenant_id.in_(tenant_ids)).group_by(Usuario.tenant_id)
    )).all())
    contagem_alunos = dict((await db.execute(
        select(Aluno.tenant_id, func.count(Aluno.id))
        .where(Aluno.tenant_id.in_(tenant_ids)).group_by(Aluno.tenant_id)
    )).all())
    contagem_professores = dict((await db.execute(
        select(Professor.tenant_id, func.count(Professor.id))
        .where(Professor.tenant_id.in_(tenant_ids)).group_by(Professor.tenant_id)
    )).all())

    return [
        {
            "id": t.id,
            "nome_fantasia": t.nome_fantasia,
            "razao_social": t.razao_social,
            "nif": t.nif,
            "status": t.status,
            "data_criacao": t.data_criacao,
            "total_usuarios": contagem_usuarios.get(t.id, 0),
            "total_alunos": contagem_alunos.get(t.id, 0),
            "total_professores": contagem_professores.get(t.id, 0),
        }
        for t in tenants
    ]


async def atualizar_status_tenant(db: AsyncSession, tenant_id: uuid.UUID, dados: TenantStatusUpdate) -> Tenant:
    """Suspende ou reativa uma instituição — RN02: bloqueia o login de todos os seus utilizadores (ver cruds/auth.py::autenticar)."""
    if dados.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use um de: {', '.join(sorted(STATUS_VALIDOS))}.")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    if tenant.nif == NIF_PLATAFORMA:
        raise HTTPException(status_code=400, detail="Não é possível alterar o estado do tenant interno da plataforma.")

    tenant.status = dados.status
    await db.commit()
    await db.refresh(tenant)
    return tenant
