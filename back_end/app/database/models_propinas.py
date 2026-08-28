"""Tabela de propinas — valores de mensalidade/matrícula que o Gestor
ou a Secretaria definem por Série/Ano (classe), por ano letivo.

Como Série/Ano já pertence sempre a um Curso (ver
models_academico.py::SerieAno), definir aqui cobre os dois casos
pedidos ("por curso ou por classe"): um preço uniforme em todas as
séries de um curso é só repetir o mesmo valor nelas; um preço por
classe é dar valores diferentes a cada série.

Isto é um catálogo de referência para a equipa consultar/negociar — não
está ligado (nesta primeira versão) à criação de Contrato Financeiro em
si (ver models_financeiro.py::ContratoFinanceiro), que continua a
receber o valor manualmente.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class PropinaSerie(Base):
    __tablename__ = "propina_serie"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    serie_ano_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("serie_ano.id", ondelete="CASCADE"), nullable=False)

    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_mensalidade: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Taxa de matrícula (paga uma vez, não confundir com a mensalidade) — opcional.
    valor_matricula: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        # Um valor por série, por ano letivo — reavaliar o preço de um
        # ano para o outro fica registado, em vez de sobrescrever.
        UniqueConstraint("serie_ano_id", "ano_letivo", name="uq_propina_serie_ano"),
    )
