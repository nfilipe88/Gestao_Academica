import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models import Base

class Aluno(Base):
    """Cadastro base do aluno (Nível 1 do documento de arquitetura).

    usuario_id é opcional nesta fase: um aluno pode existir no cadastro
    da escola sem ter login próprio na plataforma (ex: o Portal do
    Aluno ainda não foi construído). Quando existir, nome_completo e
    numero_documento passam a poder ser lidos a partir do Usuario
    associado, mas por agora o Aluno guarda os seus próprios dados para
    não depender disso.
    """
    __tablename__ = "aluno"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    matricula_interna: Mapped[str] = mapped_column(String(50), nullable=False) # Número de registo (RA) na escola
    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(50), nullable=True) # NIF/Cartão de Cidadão
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    responsaveis: Mapped[list["AlunoResponsavel"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "matricula_interna", name="uq_aluno_tenant_matricula"),
    )

class ResponsavelFinanceiroLegal(Base):
    """Responsável (Pai, Mãe, Tutor, ...) que pode ser vinculado a um ou mais alunos."""
    __tablename__ = "responsavel_financeiro_legal"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(50), nullable=True)
    telefone_contato: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True) # Para notificações (ex: vínculo a um aluno)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    alunos: Mapped[list["AlunoResponsavel"]] = relationship(back_populates="responsavel", cascade="all, delete-orphan")

class AlunoResponsavel(Base):
    """Relação N:M entre Aluno e Responsavel_Financeiro_Legal.

    Um aluno pode ter vários responsáveis (Pai, Mãe, ...) e um
    responsável pode ter vários educandos; só um por aluno costuma
    estar marcado como responsavel_financeiro (quem paga), mas isso não
    é validado aqui — é regra de negócio do módulo financeiro (Nível 2).
    """
    __tablename__ = "aluno_responsavel"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("responsavel_financeiro_legal.id", ondelete="CASCADE"), nullable=False)

    tipo_parentesco: Mapped[str] = mapped_column(String(50), nullable=False) # Ex: Pai, Mãe, Avô, Tutor
    responsavel_financeiro: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    aluno: Mapped["Aluno"] = relationship(back_populates="responsaveis")
    responsavel: Mapped["ResponsavelFinanceiroLegal"] = relationship(back_populates="alunos")

    __table_args__ = (
        UniqueConstraint("aluno_id", "responsavel_id", name="uq_aluno_responsavel"),
    )

class Professor(Base):
    """Cadastro de professor.

    Ao contrário de Aluno/ResponsavelFinanceiroLegal, aqui usuario_id
    NÃO é opcional: o documento de arquitetura já prevê que o professor
    tenha login próprio (vai precisar de aceder ao Diário de Classe no
    futuro), por isso criar um Professor cria sempre também a conta de
    Usuario (perfil_acesso=PROFESSOR) junto — ver POST /api/v1/professores.
    """
    __tablename__ = "professor"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, unique=True)

    formacao_academica: Mapped[str] = mapped_column(String(255), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
