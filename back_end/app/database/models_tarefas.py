import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class Tarefa(Base):
    """
    Trabalho/tarefa atribuído pelo professor a uma turma+disciplina —
    distinto de RegistroNota (Diário): tem prazo de entrega e uma
    avaliação por aluno com status de entrega, não só um valor.

    Liga-se a uma alocação já existente (Professor_Turma_Disciplina),
    nunca duplica professor_id/turma_id/disciplina_id diretamente —
    mesmo princípio já usado em Horários.
    """
    __tablename__ = "tarefa"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    alocacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professor_turma_disciplina.id", ondelete="CASCADE"), nullable=False)

    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_entrega: Mapped[date] = mapped_column(Date, nullable=False)
    valor_maximo: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("10.00"))
    # Opcional — se preenchido e o período (Diário) estiver trancado,
    # bloqueia a avaliação (mesma RN03 do Diário de Classe).
    periodo_avaliacao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class TarefaAvaliacao(Base):
    """
    A entrega/avaliação de UM aluno para UMA tarefa. Nasce PENDENTE
    (uma linha por aluno matriculado ATIVO) assim que a tarefa é
    criada — cruds/tarefas.py também preenche em atraso quem se
    matriculou depois — e é atualizada quando o professor avalia.
    """
    __tablename__ = "tarefa_avaliacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    tarefa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tarefa.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)

    # PENDENTE (ainda não avaliado), ENTREGUE, ENTREGUE_ATRASADO, NAO_ENTREGUE
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE")
    nota: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_avaliacao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tarefa_id", "matricula_id", name="uq_tarefa_avaliacao_tarefa_matricula"),
    )
