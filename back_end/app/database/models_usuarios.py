import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class UsuarioAuditoria(Base):
    """
    Rasto de ações sensíveis de RBAC sobre uma conta (Núcleo Multi-Tenant):
    criação de conta de Secretaria, mudança de perfil_acesso, suspensão
    e reativação — quem fez, quando, e o antes/depois. Gerada por
    cruds/usuarios.py, nunca escrita diretamente por um endpoint.

    Escrita tanto pelo Gestor (gere o pessoal da própria escola) como
    pelo Super Admin (gere qualquer escola) — por isso tenant_id é
    sempre o do UTILIZADOR ALVO da ação, não o de quem a executou (o
    Super Admin não tem tenant_id de escola nenhuma).
    """
    __tablename__ = "usuario_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    usuario_alvo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    # SET NULL (não CASCADE): o autor pode ser de outro tenant (Super
    # Admin) e o registo de auditoria deve sobreviver mesmo que a conta
    # de quem executou a ação deixe de existir.
    autor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    # CRIACAO_SECRETARIA, MUDANCA_PERFIL, SUSPENSAO, REATIVACAO
    acao: Mapped[str] = mapped_column(String(30), nullable=False)
    perfil_anterior: Mapped[str | None] = mapped_column(String(50), nullable=True)
    perfil_novo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_acao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
