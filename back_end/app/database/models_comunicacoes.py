import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class Comunicado(Base):
    """Comunicado/Convocatória enviado a Turma, Aluno ou toda a Escola.

    Guarda um registo histórico do que foi enviado (quem, quando, para
    quem, quantos destinatários) — o envio em si (e-mails individuais)
    é feito em background e não fica aqui, só a contagem.
    """
    __tablename__ = "comunicado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    tipo: Mapped[str] = mapped_column(String(20), nullable=False) # COMUNICADO, CONVOCATORIA
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)

    destinatario_tipo: Mapped[str] = mapped_column(String(20), nullable=False) # TURMA, ALUNO, ESCOLA
    destinatario_turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="SET NULL"), nullable=True)
    destinatario_aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="SET NULL"), nullable=True)

    total_destinatarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_envio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
