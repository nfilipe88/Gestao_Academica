import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Integer, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models import Base # A nossa Base declarativa original

class Curso(Base):
    __tablename__ = "curso"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Relação obrigatória com a Instituição (Isolamento)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    nome: Mapped[str] = mapped_column(String(150), nullable=False)

    # Relacionamento (Um Curso tem muitas Séries/Anos, ex: "Ensino Secundário" -> "10º Ano", "11º Ano")
    series: Mapped[list["SerieAno"]] = relationship(back_populates="curso", cascade="all, delete-orphan")

    # Presença deste curso na página pública da escola (ver
    # app/api/v1/publico.py::obter_site_publico) — nada aparece por
    # omissão, o Gestor/Secretaria decide curso a curso o que mostrar
    # (gerido em Cursos, não em Configurações > Site Público, já que é
    # informação do próprio curso). "descricao" é o conteúdo
    # programático em texto livre (o que o aluno vai aprender) — nada a
    # ver com a grade curricular interna (Disciplina/GradeCurricular),
    # que é informação de gestão, não de marketing.
    site_publico_visivel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    site_publico_descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

class SerieAno(Base):
    """Camada intermédia entre Curso e Turma (ex: "10º Ano" dentro de "Ensino Secundário").

    Uma Turma nunca se liga diretamente a um Curso — liga-se sempre a uma
    Série/Ano, que por sua vez pertence a um Curso.
    """
    __tablename__ = "serie_ano"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    curso_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("curso.id", ondelete="CASCADE"), nullable=False)

    nome: Mapped[str] = mapped_column(String(100), nullable=False) # Ex: "10º Ano", "1ª Série"

    # Relacionamentos
    curso: Mapped["Curso"] = relationship(back_populates="series")
    turmas: Mapped[list["Turma"]] = relationship(back_populates="serie_ano", cascade="all, delete-orphan")

class Turma(Base):
    __tablename__ = "turma"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    serie_ano_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("serie_ano.id", ondelete="CASCADE"), nullable=False)

    nome_codigo: Mapped[str] = mapped_column(String(50), nullable=False) # Ex: 10º Ano - Turma A
    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)     # Ex: 2024
    vagas_maximas: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Relacionamento
    serie_ano: Mapped["SerieAno"] = relationship(back_populates="turmas")

class Disciplina(Base):
    """Uma matéria lecionada na escola (ex: Matemática, História).

    Não pertence a nenhum Curso/Série diretamente — a ligação é feita
    via Grade_Curricular (quais disciplinas pertencem a cada Série/Ano).
    """
    __tablename__ = "disciplina"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    carga_horaria_total: Mapped[int] = mapped_column(Integer, nullable=True)

class GradeCurricular(Base):
    """Relação N:M entre Série/Ano e Disciplina: quais matérias pertencem a qual ano."""
    __tablename__ = "grade_curricular"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    serie_ano_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("serie_ano.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("serie_ano_id", "disciplina_id", name="uq_grade_serie_disciplina"),
    )


class ObjetivoAprendizagem(Base):
    """Um tópico/objetivo de aprendizagem dentro de uma disciplina (ex.:
    "Células" em Ciências) — catálogo mantido pela escola (Gestor/
    Secretaria) para permitir agregar o desempenho dos alunos por
    assunto, não só pela disciplina inteira. Cada Avaliacao (ver
    models_diario.py) pode, opcionalmente, apontar para um destes —
    é essa ligação que o Painel de Indicadores usa para responder
    "os alunos aprenderam bem X?" em vez de só "qual a média a Ciências?".
    """
    __tablename__ = "objetivo_aprendizagem"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    nome: Mapped[str] = mapped_column(String(150), nullable=False)  # Ex: "Células"
    descricao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("disciplina_id", "nome", name="uq_objetivo_disciplina_nome"),
    )
