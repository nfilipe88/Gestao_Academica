import uuid
from datetime import datetime
from typing import List
from sqlalchemy import String, ForeignKey, DateTime, text
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
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

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