"""
Acesso a dados do Painel Super Admin.

Ao contrário de todos os outros módulos, este é intencionalmente
multi-tenant na leitura: nenhuma função aqui filtra por tenant_id — é
o Super Admin quem gere as instituições em si. Só é alcançável através
de exigir_perfil("SUPER_ADMIN") na camada de API (app/api/v1/admin.py).
"""
import logging
import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_pessoas import Aluno, Professor
from app.schemas.admin import TenantStatusUpdate, ValidadeLicencaUpdate
from app.cruds import notificacoes as crud_notificacoes

logger = logging.getLogger("admin")

STATUS_VALIDOS = {"ATIVO", "SUSPENSO"}

# NIF reservado ao tenant interno da plataforma (onde vivem os logins
# SUPER_ADMIN, criado por seed_super_admin.py) — nunca aparece na lista
# de escolas geridas, nem pode ser suspenso.
NIF_PLATAFORMA = "00000000000"

# A partir de quantos dias antes de expirar é que a licença começa a
# gerar alertas diários (in-app + e-mail) ao Gestor da escola e ao Super Admin.
DIAS_ALERTA_LICENCA = 7


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
            "data_validade_licenca": t.data_validade_licenca,
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


async def atualizar_validade_licenca(db: AsyncSession, tenant_id: uuid.UUID, dados: ValidadeLicencaUpdate) -> Tenant:
    """Define (ou remove, se None) a data de validade da licença — ver job_validade_licenca_diaria no scheduler."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    if tenant.nif == NIF_PLATAFORMA:
        raise HTTPException(status_code=400, detail="Não é possível definir validade de licença para o tenant interno da plataforma.")

    tenant.data_validade_licenca = dados.data_validade_licenca
    await db.commit()
    await db.refresh(tenant)
    return tenant


# ==========================================
# JOB DIÁRIO (chamado por app/core/scheduler.py)
# ==========================================
async def _destinatarios_alerta_licenca(db: AsyncSession, tenant_id) -> list[uuid.UUID]:
    """GESTOR(es) da escola + todos os logins SUPER_ADMIN."""
    gestores = (await db.execute(
        select(Usuario.id).where(Usuario.tenant_id == tenant_id, Usuario.perfil_acesso == "GESTOR")
    )).scalars().all()

    tenant_plataforma = (await db.execute(select(Tenant.id).where(Tenant.nif == NIF_PLATAFORMA))).scalar_one_or_none()
    super_admins = []
    if tenant_plataforma:
        super_admins = (await db.execute(
            select(Usuario.id).where(Usuario.tenant_id == tenant_plataforma, Usuario.perfil_acesso == "SUPER_ADMIN")
        )).scalars().all()

    return list(gestores) + list(super_admins)


async def processar_validade_licencas(db: AsyncSession, agendar_email) -> dict:
    """
    Percorre todas as escolas com data de validade de licença definida:
    - já expirada e ainda ATIVO -> suspende automaticamente + notifica.
    - a expirar dentro de DIAS_ALERTA_LICENCA e ATIVO -> só alerta
      (repete todos os dias dentro da janela — intencional, para o
      Gestor não perder o aviso).
    Devolve um resumo para o log/teste manual.
    """
    hoje = date.today()
    limite_alerta = hoje + timedelta(days=DIAS_ALERTA_LICENCA)

    tenants = (await db.execute(
        select(Tenant).where(
            Tenant.nif != NIF_PLATAFORMA,
            Tenant.data_validade_licenca.isnot(None),
            Tenant.status == "ATIVO",
        )
    )).scalars().all()

    resumo = {"suspensos": 0, "alertados": 0}

    for tenant in tenants:
        destinatarios = await _destinatarios_alerta_licenca(db, tenant.id)
        emails = (await db.execute(
            select(Usuario.email).where(Usuario.id.in_(destinatarios))
        )).scalars().all() if destinatarios else []

        if tenant.data_validade_licenca < hoje:
            tenant.status = "SUSPENSO"
            titulo = "Licença expirada — acesso suspenso"
            mensagem = f"A licença de {tenant.nome_fantasia} expirou em {tenant.data_validade_licenca.strftime('%d/%m/%Y')} e o acesso foi automaticamente suspenso."
            resumo["suspensos"] += 1
        elif tenant.data_validade_licenca <= limite_alerta:
            dias_restantes = (tenant.data_validade_licenca - hoje).days
            titulo = "Licença a expirar em breve"
            mensagem = f"A licença de {tenant.nome_fantasia} expira em {tenant.data_validade_licenca.strftime('%d/%m/%Y')} ({dias_restantes} dia(s))."
            resumo["alertados"] += 1
        else:
            continue

        try:
            await crud_notificacoes.criar_notificacoes_em_lote(
                db, tenant.id, destinatarios, tipo="LICENCA", titulo=titulo, mensagem=mensagem, link="/admin"
            )
            await db.commit()
        except Exception:
            logger.exception("Falha ao notificar/atualizar a licença da escola %s (%s).", tenant.nome_fantasia, tenant.id)
            await db.rollback()
            continue

        from app.core.email import enviar_email, template_base
        for email in emails:
            if email:
                await agendar_email(enviar_email, destinatario=email, assunto=titulo, corpo_html=template_base(titulo, f"<p>{mensagem}</p>"))

    return resumo
