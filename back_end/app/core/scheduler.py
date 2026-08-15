"""
Agendador interno (APScheduler, in-process — sem serviço externo tipo
Celery/Redis) para tarefas que o documento de arquitetura pede como
automáticas mas que, até agora, só corriam quando alguém clicava num
botão.

RN04 do Financeiro (régua de cobrança): o endpoint
POST /financeiro/regua-cobranca/processar continua a existir para
disparo manual/teste, mas a partir de agora corre sozinho todos os
dias, para todas as escolas — não é preciso o Gestor lembrar-se de
clicar.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, text

from app.database.session import AsyncSessionLocal
from app.database.models import Tenant
from app.cruds.financeiro import processar_regua_cobranca_do_tenant
from app.cruds.admin import processar_validade_licencas
from app.core.email import enviar_email

logger = logging.getLogger("scheduler")

_scheduler: AsyncIOScheduler | None = None


async def _enviar_email_direto(func, **kwargs):
    """No scheduler não há um pedido HTTP para não bloquear — enviar já, em vez de agendar."""
    await func(**kwargs)


async def job_regua_de_cobranca_diaria() -> dict:
    """
    Percorre todas as escolas ATIVAS e processa a régua de cobrança de
    cada uma. Falhas numa escola ficam registadas em log mas não
    impedem o processamento das restantes (uma escola com dados
    inconsistentes não deve bloquear o envio de lembretes a todas as outras).
    """
    resumo: dict[str, int] = {}

    async with AsyncSessionLocal() as db:
        tenants = (await db.execute(select(Tenant).where(Tenant.status == "ATIVO"))).scalars().all()

    logger.info("Régua de cobrança diária: a processar %d escola(s) ativa(s).", len(tenants))

    for tenant in tenants:
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(tenant.id)})
                contagem = await processar_regua_cobranca_do_tenant(db, tenant.id, _enviar_email_direto)
                resumo[str(tenant.id)] = sum(contagem.values())
        except Exception:
            logger.exception("Falha ao processar a régua de cobrança da escola %s (%s).", tenant.nome_fantasia, tenant.id)

    total = sum(resumo.values())
    logger.info("Régua de cobrança diária concluída: %d e-mail(s) despachado(s) no total.", total)
    return resumo


async def job_validade_licenca_diaria() -> dict:
    """
    RN do Super Admin: escolas com data_validade_licenca definida são
    alertadas (in-app + e-mail) nos DIAS_ALERTA_LICENCA dias antes de
    expirar, e suspensas automaticamente (status=SUSPENSO) assim que a
    data passa — sem exigir que o Super Admin se lembre de agir.
    """
    async with AsyncSessionLocal() as db:
        try:
            resumo = await processar_validade_licencas(db, _enviar_email_direto)
        except Exception:
            logger.exception("Falha ao processar a validade das licenças.")
            return {"suspensos": 0, "alertados": 0}

    logger.info(
        "Validade de licenças diária concluída: %d escola(s) suspensa(s), %d alerta(s) enviado(s).",
        resumo["suspensos"], resumo["alertados"]
    )
    return resumo


def iniciar_scheduler() -> AsyncIOScheduler:
    """Chamado uma vez, no arranque da aplicação (ver main.py)."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler()
    # 08:00 — horário em que a secretaria já está a trabalhar, para
    # poder acompanhar/responder a dúvidas dos responsáveis no próprio dia.
    _scheduler.add_job(
        job_regua_de_cobranca_diaria,
        trigger=CronTrigger(hour=8, minute=0),
        id="regua_cobranca_diaria",
        replace_existing=True,
    )
    # 07:00 — antes da régua de cobrança, para uma escola recém-suspensa
    # por licença expirada já não disparar lembretes de mensalidade no
    # mesmo dia.
    _scheduler.add_job(
        job_validade_licenca_diaria,
        trigger=CronTrigger(hour=7, minute=0),
        id="validade_licenca_diaria",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler iniciado — validade de licenças às 07:00 e régua de cobrança às 08:00, todos os dias.")
    return _scheduler


def parar_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
