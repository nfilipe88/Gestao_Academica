import uuid
from datetime import date, datetime
from typing import List
from sqlalchemy import Date, String, ForeignKey, DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome_fantasia: Mapped[str] = mapped_column(String(255), nullable=False)
    razao_social: Mapped[str] = mapped_column(String(255), nullable=True)
    nif: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ATIVO")
    # Validade da licença de acesso à plataforma — nullable (sem data
    # definida = sem expiração automática, ex.: o tenant interno da
    # plataforma). Gerido pelo Super Admin; job diário do scheduler
    # alerta a aproximar-se e suspende automaticamente ao expirar (ver
    # app/core/scheduler.py::job_validade_licenca_diaria).
    data_validade_licenca: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Configurações da escola (editável pelo próprio GESTOR, ao contrário
    # dos campos acima que são geridos pelo Super Admin) — ver
    # app/api/v1/configuracoes.py. Tudo nullable: uma escola nova não é
    # obrigada a preencher isto antes de poder usar a plataforma.
    iban: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Código ISO 4217 (EUR, USD, ...) — controla a moeda mostrada em toda
    # a plataforma E a moeda enviada ao PayPal nas cobranças (ver
    # app/core/paypal.py). Por isso é restrita, no schema Pydantic, à
    # lista de moedas que o PayPal realmente aceita — nunca um código
    # livre que depois falharia silenciosamente na cobrança.
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR", server_default="EUR")
    telefone_contacto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email_contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    morada: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pais: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relacionamento
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil_acesso: Mapped[str] = mapped_column(String(50), nullable=False) # GESTOR, PROFESSOR, ALUNO
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relacionamento
    tenant: Mapped["Tenant"] = relationship(back_populates="usuarios")