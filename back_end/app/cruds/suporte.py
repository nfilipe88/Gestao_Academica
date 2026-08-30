import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Tenant, Usuario
from app.database.models_suporte import ESTADOS_TICKET, TicketMensagem, TicketSuporte
from app.schemas.suporte import MensagemTicketCreate, TicketCreate
from app.core.paginacao import DEFAULT_PAGE_SIZE, paginar, paginar_linhas
from app.core import fila_notificacoes
from app.core.email import enviar_email, template_base


async def _criar_ticket(db: AsyncSession, tenant_id: uuid.UUID | None, autor_nome: str, autor_email: str, dados: TicketCreate) -> TicketSuporte:
    ticket = TicketSuporte(tenant_id=tenant_id, autor_nome=autor_nome, autor_email=autor_email, assunto=dados.assunto)
    db.add(ticket)
    await db.flush()
    db.add(TicketMensagem(ticket_id=ticket.id, tenant_id=tenant_id, autor_tipo="CLIENTE", autor_nome=autor_nome, corpo=dados.mensagem))
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def criar_ticket_publico(db: AsyncSession, dados: TicketCreate) -> TicketSuporte:
    """Visitante do site, sem sessão (ver /contacto) — tenant_id fica None."""
    return await _criar_ticket(db, None, dados.nome, dados.email, dados)


async def criar_ticket_autenticado(db: AsyncSession, tenant_id: uuid.UUID, autor_nome: str, autor_email: str, dados: TicketCreate) -> TicketSuporte:
    """Staff já autenticado, a abrir o ticket de dentro da app — nome/e-mail vêm da conta, não do formulário."""
    return await _criar_ticket(db, tenant_id, autor_nome, autor_email, dados)


async def listar_meus_tickets(db: AsyncSession, tenant_id: uuid.UUID, page: int, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    query = select(TicketSuporte).where(TicketSuporte.tenant_id == tenant_id).order_by(TicketSuporte.atualizado_em.desc())
    return await paginar(db, query, page, page_size)


async def obter_meu_ticket(db: AsyncSession, ticket_id: uuid.UUID, tenant_id: uuid.UUID) -> TicketSuporte:
    ticket = (await db.execute(
        select(TicketSuporte).options(selectinload(TicketSuporte.mensagens))
        .where(TicketSuporte.id == ticket_id, TicketSuporte.tenant_id == tenant_id)
    )).scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado.")
    return ticket


async def adicionar_mensagem_cliente(db: AsyncSession, ticket_id: uuid.UUID, tenant_id: uuid.UUID, usuario_id: uuid.UUID, dados: MensagemTicketCreate) -> TicketMensagem:
    ticket = await obter_meu_ticket(db, ticket_id, tenant_id)
    nome_usuario = (await db.execute(select(Usuario.nome_completo).where(Usuario.id == usuario_id))).scalar_one_or_none()
    msg = TicketMensagem(ticket_id=ticket.id, tenant_id=tenant_id, autor_tipo="CLIENTE", autor_nome=nome_usuario or ticket.autor_nome, corpo=dados.corpo)
    db.add(msg)
    # Reabre o ticket automaticamente se o cliente escreveu depois de já
    # estar Resolvido/Fechado — sem isto, o Super Admin nunca via que
    # havia conversa nova, um ticket "fechado" ficava fechado para sempre.
    if ticket.estado in ("RESOLVIDO", "FECHADO"):
        ticket.estado = "EM_ANDAMENTO"
    await db.commit()
    await db.refresh(msg)
    return msg


# ==========================================
# Super Admin — cross-tenant
# ==========================================

async def listar_tickets_admin(db: AsyncSession, page: int, page_size: int = DEFAULT_PAGE_SIZE, estado: str | None = None) -> dict:
    query = (
        select(TicketSuporte, Tenant.nome_fantasia)
        .outerjoin(Tenant, Tenant.id == TicketSuporte.tenant_id)
        .order_by(TicketSuporte.atualizado_em.desc())
    )
    if estado:
        query = query.where(TicketSuporte.estado == estado)
    pagina = await paginar_linhas(db, query, page, page_size)
    pagina["items"] = [
        {
            "id": t.id, "tenant_id": t.tenant_id, "nome_escola": nome_escola,
            "autor_nome": t.autor_nome, "autor_email": t.autor_email, "assunto": t.assunto,
            "estado": t.estado, "criado_em": t.criado_em, "atualizado_em": t.atualizado_em,
        }
        for t, nome_escola in pagina["items"]
    ]
    return pagina


async def obter_ticket_admin(db: AsyncSession, ticket_id: uuid.UUID) -> TicketSuporte:
    ticket = (await db.execute(
        select(TicketSuporte).options(selectinload(TicketSuporte.mensagens)).where(TicketSuporte.id == ticket_id)
    )).scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado.")
    return ticket


async def responder_ticket_admin(db: AsyncSession, ticket_id: uuid.UUID, dados: MensagemTicketCreate) -> TicketMensagem:
    ticket = await obter_ticket_admin(db, ticket_id)
    msg = TicketMensagem(ticket_id=ticket.id, tenant_id=ticket.tenant_id, autor_tipo="SUPORTE", autor_nome="Equipa SaaS Académico", corpo=dados.corpo)
    db.add(msg)
    if ticket.estado == "ABERTO":
        ticket.estado = "EM_ANDAMENTO"
    await db.commit()
    await db.refresh(msg)

    # Um visitante anónimo (tenant_id None) não tem nenhuma área da app
    # onde ver a resposta — o e-mail é a única forma de a receber. Um
    # ticket de uma escola já cliente fica visível em "Suporte" dentro
    # da própria app, não precisa de e-mail extra.
    if ticket.tenant_id is None:
        corpo_html = template_base(
            f"Resposta ao seu pedido: {ticket.assunto}",
            f"<p>{dados.corpo}</p><p style='margin-top:16px;color:#64748b;font-size:13px;'>Pode responder diretamente a este e-mail para continuar a conversa.</p>"
        )
        await fila_notificacoes.agendar_email(
            enviar_email, destinatario=ticket.autor_email, assunto=f"Re: {ticket.assunto}", corpo_html=corpo_html
        )
    return msg


async def atualizar_estado_admin(db: AsyncSession, ticket_id: uuid.UUID, estado: str) -> TicketSuporte:
    if estado not in ESTADOS_TICKET:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Use um de: {', '.join(ESTADOS_TICKET)}.")
    ticket = await obter_ticket_admin(db, ticket_id)
    ticket.estado = estado
    await db.commit()
    await db.refresh(ticket)
    return ticket
