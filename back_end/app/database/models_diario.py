import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class ProfessorTurmaDisciplina(Base):
    """Alocação de docentes: define que um Professor lecciona uma
    Disciplina numa Turma. É a base do Diário de Classe — RN01 exige
    validar que quem lança notas/faltas é realmente o professor alocado.
    """
    __tablename__ = "professor_turma_disciplina"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    professor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professor.id", ondelete="CASCADE"), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("professor_id", "turma_id", "disciplina_id", name="uq_alocacao_professor_turma_disciplina"),
    )

class RegistroFrequencia(Base):
    """Diário - Chamada. Um registo por aluno, por disciplina, por dia de aula."""
    __tablename__ = "registro_frequencia"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    data_aula: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade_aulas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    conteudo_programado: Mapped[str] = mapped_column(String(500), nullable=True)
    presenca: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    faltas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Um só registo por aluno/disciplina/dia — lançar de novo faz upsert.
        UniqueConstraint("matricula_id", "disciplina_id", "data_aula", name="uq_frequencia_matricula_disciplina_data"),
    )

class RegistroNota(Base):
    """Diário - Avaliação. Uma nota por aluno, disciplina e período de avaliação."""
    __tablename__ = "registro_nota"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    periodo_avaliacao: Mapped[str] = mapped_column(String(50), nullable=False) # Ex: "1º Bimestre"
    tipo_avaliacao: Mapped[str] = mapped_column(String(50), nullable=True) # Ex: "Prova Escrita"
    data_avaliacao: Mapped[date] = mapped_column(Date, nullable=True)
    valor_nota: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Upsert target: relançar a nota do mesmo aluno/disciplina/período atualiza, não duplica.
        UniqueConstraint("matricula_id", "disciplina_id", "periodo_avaliacao", name="uq_nota_matricula_disciplina_periodo"),
    )

class RegistroNotaAuditoria(Base):
    """RN04: sempre que uma nota já existente é alterada, fica aqui o rasto
    (quem alterou, quando, valor antigo e novo) — não é criado no primeiro
    lançamento, só nas alterações seguintes.
    """
    __tablename__ = "registro_nota_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    registro_nota_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("registro_nota.id", ondelete="CASCADE"), nullable=False)
    alterado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    valor_antigo: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    valor_novo: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    alterado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
