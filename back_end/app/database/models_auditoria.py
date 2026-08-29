import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class AuditLog(Base):
    """
    Trilha de auditoria GERAL da plataforma — quem, quando e o quê foi
    criado/alterado/apagado, em qualquer entidade do sistema (Aluno,
    Matricula, Fatura, PlanoSaaS, Comunicado, ...), não só nas contas
    de utilizador (isso já existia em UsuarioAuditoria, ver
    models_usuarios.py) ou nas notas (RegistroNotaAuditoria, ver
    models_diario.py).

    Alimentada automaticamente por um listener SQLAlchemy
    (before_flush, ver app/core/auditoria.py) em cima de TODAS as
    sessões (tenant e admin) — não é escrita manualmente por nenhum
    crud, por isso cobre entidades novas sem precisar de código extra
    em cada módulo.
    """
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Nullable: ações verdadeiramente públicas (captação de Lead antes
    # de existir tenant conhecido, webhook de pagamento antes de
    # encontrar a Transacao_Gateway) podem correr na sessão "pública"
    # sem tenant_id definido no contexto — nesses casos o listener usa
    # o tenant_id da própria entidade alterada, que normalmente já
    # existe na linha. Quando mesmo assim não há nenhum, fica NULL em
    # vez de rejeitar o registo de auditoria.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=True)

    # SET NULL, não CASCADE: o registo de auditoria tem de sobreviver
    # mesmo que a conta de quem executou a ação seja apagada depois.
    autor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    autor_perfil: Mapped[str | None] = mapped_column(String(50), nullable=True)

    acao: Mapped[str] = mapped_column(String(10), nullable=False)  # CRIADO, ALTERADO, APAGADO
    entidade: Mapped[str] = mapped_column(String(80), nullable=False)  # __tablename__ do modelo (ex.: "aluno", "fatura_mensalidade")
    entidade_id: Mapped[str] = mapped_column(String(64), nullable=False)  # chave primária como texto

    # Para CRIADO/APAGADO: snapshot de todas as colunas (não sensíveis).
    # Para ALTERADO: só os campos que mudaram, {campo: {antes, depois}}.
    alteracoes: Mapped[dict] = mapped_column(JSONB, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Consultar o histórico de UM registo específico (ex.: "quem mexeu nesta fatura?").
        Index("ix_audit_log_entidade", "entidade", "entidade_id"),
        # Feed de atividade recente de uma escola.
        Index("ix_audit_log_tenant_criado_em", "tenant_id", "criado_em"),
        Index("ix_audit_log_autor", "autor_id"),
    )
