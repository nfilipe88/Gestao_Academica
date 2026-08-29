"""SaaS Billing do Super Admin — planos, assinaturas e MRR.

Distinto de app/database/models.py::Tenant.data_validade_licenca (que
continua a existir e a controlar o acesso em si, via
app/core/scheduler.py::job_validade_licenca_diaria): este módulo
descreve o CONTRATO comercial (que plano, quanto paga, quando é a
próxima cobrança) — a validade da licença é a consequência de pagar
ou não, não o mesmo conceito.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models import Base


class PlanoSaaS(Base):
    """Catálogo de planos comerciais (ex.: Bronze/Prata/Ouro) — global à
    plataforma, não tenant-scoped (só o Super Admin gere isto, através
    de obter_sessao_db_admin), por isso sem RLS."""
    __tablename__ = "plano_saas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    # Substitui o antigo preco_mensal fixo (Fase "planos por aluno/
    # módulo") — a mensalidade de uma escola passa a ser
    # preco_por_aluno × nº de alunos cadastrados na escola, mais o que
    # os módulos incluídos (ver PlanoSaaSModulo) custarem à parte. Ver
    # cruds/admin.py::obter_resumo_mrr para o cálculo completo.
    preco_por_aluno: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # None = sem limite (plano topo de gama) — usado só para referência
    # comercial nesta primeira versão, ainda não faz cumprir o limite
    # em nenhum outro módulo.
    limite_alunos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descricao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Dias de período de teste oferecidos ao atribuir este plano a uma
    # escola nova (0 = sem teste, cobrança normal desde o início). Só
    # define a duração do teste — "está em período de teste?" é
    # calculado on-the-fly a partir de AssinaturaTenant.data_inicio +
    # este valor, nunca persistido (ver cruds/admin.py::_em_periodo_teste).
    dias_periodo_teste: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    modulos: Mapped[list["PlanoSaaSModulo"]] = relationship(cascade="all, delete-orphan")


class PlanoSaaSModulo(Base):
    """Módulos da plataforma incluídos num plano, cada um com o seu
    próprio preço adicional (0 = incluído sem custo extra) — usa a
    MESMA lista de módulos do Mapa de Permissões
    (alembic/versions/584537bbba2e_permissao_modulo.py::MODULOS), para
    não haver dois vocabulários de "módulo" diferentes na plataforma.

    Um módulo AUSENTE desta tabela para um plano = não incluído: a
    plataforma bloqueia mesmo o acesso (ver app/core/modulos.py —
    exigir_modulo), não é só uma questão de preço. Nem todos os
    módulos são "gateáveis" — os fundamentais (Alunos, Turmas,
    Configurações, ...) continuam sempre acessíveis independentemente
    do plano; ver MODULOS_GATEAVEIS em app/core/modulos.py."""
    __tablename__ = "plano_saas_modulo"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plano_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plano_saas.id", ondelete="CASCADE"), nullable=False)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False)
    preco_adicional: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("plano_id", "modulo", name="uq_plano_saas_modulo"),
    )


class AssinaturaTenant(Base):
    """A subscrição comercial de uma escola a um plano — uma por tenant
    (a mais recente substitui a anterior, ver cruds/admin.py::definir_assinatura_tenant).
    Tem RLS (ao contrário de PlanoSaaS) por pertencer claramente a um
    tenant, seguindo a mesma regra do resto da plataforma, mesmo só
    sendo lida/escrita hoje pela sessão de sistema do Super Admin."""
    __tablename__ = "assinatura_tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    plano_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plano_saas.id", ondelete="RESTRICT"), nullable=False)

    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    proxima_cobranca: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ATIVA")  # ATIVA, CANCELADA

    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        # Uma assinatura "viva" por tenant — trocar de plano atualiza a
        # linha existente em vez de acumular histórico (fora de alcance
        # nesta primeira versão).
        UniqueConstraint("tenant_id", name="uq_assinatura_tenant_tenant"),
    )
