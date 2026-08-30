import uuid
from datetime import date, datetime, time
from typing import List
from sqlalchemy import Boolean, Date, Numeric, String, ForeignKey, DateTime, Text, Time, text
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
    # Nota mínima de aprovação (escala livre — cada escola usa a sua,
    # ex.: 0-20 ou 0-10) — usada no Boletim/Indicadores para marcar
    # Aprovado/Reprovado. Sem valor definido, essa marcação não aparece.
    nota_minima_aprovacao: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)

    # Períodos letivos (Manhã/Tarde/Pós-Laboral) — hora de início e de
    # encerramento de cada um. Só guarda a informação nesta primeira
    # versão (referência para a equipa); ainda não é usado para validar
    # conflitos em Horários (ver models_horarios.py), que continua a
    # aceitar qualquer hora informada diretamente na aula.
    periodo_manha_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_manha_fim: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_tarde_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_tarde_fim: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_pos_laboral_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_pos_laboral_fim: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Chave do logótipo no storage (app/core/storage.py) — não guarda o
    # ficheiro em si, só a referência; None = escola sem logótipo, os
    # PDFs gerados (documentos_pdf.py) mostram só o nome em texto.
    logotipo_chave: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Página pública de apresentação da própria escola (marketing/
    # angariação de alunos, distinta da apresentação da PLATAFORMA em
    # si — ver app/api/v1/publico.py::obter_site_publico) — desativada
    # por omissão: uma escola nova não fica com uma página pública a
    # meio de preencher exposta sem querer. Texto livre, sem
    # formatação — o frontend só quebra por parágrafos.
    site_publico_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    site_publico_missao: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_publico_metodologia: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def tem_logotipo(self) -> bool:
        """Não é uma coluna — só facilita expor "há logótipo?" via
        ConfiguracaoTenantOut sem vazar a chave interna do storage."""
        return self.logotipo_chave is not None

    # Relacionamento
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil_acesso: Mapped[str] = mapped_column(String(50), nullable=False) # GESTOR, PROFESSOR, ALUNO
    # Suspensão individual (distinta da suspensão da escola inteira em
    # Tenant.status) — Gestor/Super Admin usam isto para revogar o
    # acesso de UMA pessoa (ex.: funcionário que saiu) sem mexer no
    # resto da escola. Só é verificado no login (ver
    # cruds/auth.py::autenticar), não em cada pedido — mesma limitação
    # já aceite para Tenant.status: uma sessão já iniciada só perde o
    # acesso quando o token expirar (até 24h), não instantaneamente.
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relacionamento
    tenant: Mapped["Tenant"] = relationship(back_populates="usuarios")