import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class Matricula(Base):
    """O vínculo do Aluno com a Escola, numa Turma, num ano letivo.

    RN04 do documento de arquitetura: toda nova matrícula recebe
    status_matricula "ATIVO" automaticamente. As transições (Trancado,
    Transferido, Evadido) são feitas via PATCH /matriculas/{id}/status,
    nunca escritas diretamente na criação.
    """
    __tablename__ = "matricula"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)

    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)
    status_matricula: Mapped[str] = mapped_column(String(20), nullable=False, default="ATIVO") # ATIVO, TRANSFERIDO, TRANCADO, EVADIDO
    data_matricula: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # RN03 - Prevenção de Duplicidade
        UniqueConstraint("aluno_id", "turma_id", "ano_letivo", name="uq_matricula_aluno_turma_ano"),
        # "Matrículas ativas de um aluno/de uma turma" é a consulta mais
        # comum sobre esta tabela (transferências, boletim, financeiro,
        # portal) — cobre o filtro completo em vez de só tenant_id.
        Index("ix_matricula_tenant_status", "tenant_id", "status_matricula"),
    )
