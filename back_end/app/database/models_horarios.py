import uuid
from datetime import datetime, time
from sqlalchemy import DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class HorarioAula(Base):
    """
    Um "slot" fixo na grade horária semanal: esta Alocação (Professor +
    Turma + Disciplina, já validada no Nível 1) acontece neste dia da
    semana, entre esta hora de início e fim.

    Não duplica professor_id/turma_id/disciplina_id — vêm sempre de
    ProfessorTurmaDisciplina, para a grade nunca poder agendar uma
    combinação que não exista como alocação real (mesmo espírito do
    Diário de Classe: reaproveitar a Alocação em vez de reintroduzir os
    mesmos dados noutro sítio).
    """
    __tablename__ = "horario_aula"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    alocacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professor_turma_disciplina.id", ondelete="CASCADE"), nullable=False)

    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Segunda ... 7=Domingo (ISO 8601)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fim: Mapped[time] = mapped_column(Time, nullable=False)
    sala: Mapped[str | None] = mapped_column(String(50), nullable=True)

    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Evita duplicar exatamente o mesmo slot (mesma alocação, dia e
        # hora) por engano — não substitui a validação de sobreposição
        # (RN01/RN02 em app/cruds/horarios.py), que cobre também
        # intervalos parcialmente sobrepostos, não só o mesmo instante exato.
        UniqueConstraint("alocacao_id", "dia_semana", "hora_inicio", name="uq_horario_alocacao_dia_hora"),
    )
