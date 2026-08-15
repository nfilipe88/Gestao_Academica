import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class Notificacao(Base):
    """
    Alerta in-app para um utilizador específico — comunicados,
    respostas a solicitações (documentos, transferências), avisos de
    licença, etc. Criada diretamente pelo crud de origem (ver
    cruds/notificacoes.py::criar_notificacao/criar_notificacoes_em_lote),
    nunca por um endpoint público — só quem já teria de qualquer forma
    acesso ao evento de origem é que gera a notificação.
    """
    __tablename__ = "notificacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)

    # COMUNICADO, SOLICITACAO_DOCUMENTO, SOLICITACAO_TRANSFERENCIA, LICENCA, SISTEMA
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    # Rota do frontend para onde a notificação aponta (ex: "/comunicacoes") — opcional.
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)

    lida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_leitura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
