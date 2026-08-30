import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models import Base

ESTADOS_TICKET = ("ABERTO", "EM_ANDAMENTO", "RESOLVIDO", "FECHADO")


class TicketSuporte(Base):
    """
    Pedido de suporte/contacto à equipa que gere a plataforma (não é
    suporte de uma escola aos seus alunos — é uma escola, ou um
    visitante, a contactar o Super Admin).

    tenant_id nullable de propósito: um VISITANTE do site público
    (ainda sem conta nenhuma) também pode abrir um ticket a partir de
    /contacto — nesse caso tenant_id fica None e a única forma de
    responder é pelo autor_email guardado (ver
    cruds/suporte.py::responder_ticket, que envia e-mail quando não há
    tenant). Quando é staff já autenticado a abrir o ticket de dentro
    da app, tenant_id fica preenchido e a conversa fica visível no
    "Suporte" da própria escola.
    """
    __tablename__ = "ticket_suporte"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenant.id", ondelete="SET NULL"), nullable=True)
    autor_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    autor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    assunto: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ABERTO", server_default="ABERTO")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    mensagens: Mapped[list["TicketMensagem"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMensagem.criado_em"
    )

    __table_args__ = (
        Index("ix_ticket_suporte_tenant_estado", "tenant_id", "estado"),
        Index("ix_ticket_suporte_estado_criado_em", "estado", "criado_em"),
    )


class TicketMensagem(Base):
    """Uma mensagem na conversa de um ticket — CLIENTE (autor do ticket
    ou outro membro do staff da mesma escola) ou SUPORTE (Super Admin).
    tenant_id repetido do ticket-pai (denormalizado) só para a policy
    de RLS poder filtrar esta tabela diretamente, sem depender de um
    JOIN — mesma necessidade que levou a indexar tenant_id em toda a
    plataforma na Fase 6."""
    __tablename__ = "ticket_mensagem"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ticket_suporte.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenant.id", ondelete="SET NULL"), nullable=True)
    autor_tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # CLIENTE, SUPORTE
    autor_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    ticket: Mapped["TicketSuporte"] = relationship(back_populates="mensagens")

    __table_args__ = (
        Index("ix_ticket_mensagem_ticket_id", "ticket_id"),
    )
