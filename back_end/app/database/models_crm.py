import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class LeadCandidato(Base):
    """Um potencial aluno, capturado antes de existir qualquer registo académico.

    Serve de "sala de espera": só quando a Oportunidade_CRM ligada a
    este Lead é movida para uma etapa marcada como eh_etapa_ganho é que
    nasce um Aluno de verdade (ver RN01 em app/api/v1/crm.py).
    """
    __tablename__ = "lead_candidato"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    curso_interesse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("curso.id", ondelete="SET NULL"), nullable=True)

    nome_responsavel: Mapped[str] = mapped_column(String(255), nullable=False)
    email_contato: Mapped[str] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str] = mapped_column(String(50), nullable=True)

    nome_aluno_candidato: Mapped[str] = mapped_column(String(255), nullable=False)
    # Não pedido no formulário inicial (o documento só define nome_aluno_candidato
    # aqui), mas Aluno.data_nascimento é obrigatória — por isso fica opcional no
    # Lead e é exigida só no momento da conversão (RN01), não na captação.
    data_nascimento_candidato: Mapped[date | None] = mapped_column(Date, nullable=True)

    origem_lead: Mapped[str] = mapped_column(String(30), nullable=False, default="OUTRO")  # SITE, FACEBOOK, INDICACAO, PRESENCIAL, OUTRO
    data_entrada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class FunilEtapa(Base):
    """Uma coluna do quadro Kanban do CRM (ex: "Nova Lead", "Matriculado").

    eh_etapa_ganho marca qual(is) etapa(s) representam conversão bem
    sucedida — é isto (não o nome da etapa) que decide se mover uma
    Oportunidade para aqui dispara a RN01, evitando depender de
    comparar strings como "Matriculado"/"Ganho".
    """
    __tablename__ = "funil_etapa"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    nome_etapa: Mapped[str] = mapped_column(String(100), nullable=False)
    eh_etapa_ganho: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "ordem", name="uq_funil_etapa_tenant_ordem"),
    )


class OportunidadeCRM(Base):
    """O "cartão" no quadro Kanban — um Lead a percorrer o funil de vendas."""
    __tablename__ = "oportunidade_crm"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lead_candidato.id", ondelete="CASCADE"), nullable=False)
    etapa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("funil_etapa.id", ondelete="RESTRICT"), nullable=False)

    valor_estimado_anual: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    data_fecho_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Turma pretendida — extensão da RN01: só depois de a Secretaria
    # indicar isto (o CRM sozinho só conhece o Curso de interesse do
    # Lead) é que mover a oportunidade para uma etapa eh_etapa_ganho
    # também gera Matrícula + Contrato Financeiro automaticamente, e
    # não só Aluno + Responsável (ver _tentar_matricula_e_contrato_automaticos
    # em app/cruds/crm.py).
    turma_interesse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("turma.id", ondelete="SET NULL"), nullable=True)

    # Preenchidos pela RN01 quando a oportunidade é convertida — também
    # servem de marcador de idempotência (não converter duas vezes).
    aluno_gerado_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aluno.id", ondelete="SET NULL"), nullable=True)
    responsavel_gerado_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("responsavel_financeiro_legal.id", ondelete="SET NULL"), nullable=True)

    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
