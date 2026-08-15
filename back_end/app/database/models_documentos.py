"""
Solicitações de Documentos — duas direções distintas:

1. Aluno/Responsável pede um documento EMITIDO pela escola (certificado,
   declaração, histórico escolar, boletim, outro). Tem preço (tabela
   configurável pelo Gestor) e cobrança via PayPal antes da libertação;
   o PDF é gerado a partir de um layout (ver app/core/documentos_pdf.py)
   no momento do pedido de download, nunca guardado em disco — a
   plataforma não tem armazenamento de ficheiros.

2. A escola pede um documento/informação a um Aluno, Responsável ou
   Professor (ex: cópia do B.I., atestado médico). Sem preço nem PDF —
   é um ticket de estado (PENDENTE → RESPONDIDO → CONCLUIDO) para que
   toda a comunicação, mesmo quando a entrega final é física, fique
   registada na plataforma.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class PrecoDocumento(Base):
    """Tabela de preços por tipo de documento, configurável pelo Gestor."""
    __tablename__ = "preco_documento"
    __table_args__ = (UniqueConstraint("tenant_id", "tipo_documento", name="uq_preco_documento_tenant_tipo"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)

    # CERTIFICADO, DECLARACAO, HISTORICO_ESCOLAR, BOLETIM, OUTRO
    tipo_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ativo: Mapped[bool] = mapped_column(default=True, nullable=False)


class SolicitacaoDocumentoEmissao(Base):
    """Pedido de um Aluno/Responsável para a escola emitir um documento."""
    __tablename__ = "solicitacao_documento_emissao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    solicitante_usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    tipo_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    descricao_outro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # DIGITAL (só download) ou FISICA (a escola imprime; ainda gerado pela plataforma)
    formato_entrega: Mapped[str] = mapped_column(String(10), nullable=False, default="DIGITAL")

    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # snapshot no momento do pedido
    # PENDENTE_PAGAMENTO, PAGO, ENTREGUE, CANCELADO
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE_PAGAMENTO")

    paypal_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacoes_escola: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_solicitacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_pagamento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_conclusao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SolicitacaoDocumentoEscola(Base):
    """Pedido da escola a um Aluno, Responsável ou Professor."""
    __tablename__ = "solicitacao_documento_escola"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)

    # ALUNO, RESPONSAVEL, PROFESSOR — só um dos 3 FKs abaixo é preenchido.
    destinatario_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    destinatario_aluno_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=True)
    destinatario_responsavel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("responsavel_financeiro_legal.id", ondelete="CASCADE"), nullable=True)
    destinatario_professor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("professor.id", ondelete="CASCADE"), nullable=True)

    solicitado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)

    # PENDENTE, RESPONDIDO, CONCLUIDO
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE")
    resposta_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    respondido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    data_solicitacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
