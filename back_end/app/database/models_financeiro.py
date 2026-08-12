import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class ContratoFinanceiro(Base):
    """O acordo financeiro geral de um aluno para um ano letivo (Nível 2 do documento).

    Liga-se a Matricula (o quê/quando académico) e a
    ResponsavelFinanceiroLegal (quem paga). Ao ser criado, gera de
    imediato todas as parcelas (Fatura_Mensalidade) — ver
    app/api/v1/financeiro.py::criar_contrato. O documento original
    prevê geração em lote via Cron Job 15 dias antes do vencimento
    (RN01), pensada para não emitir cobranças no gateway de pagamento
    antes da hora; como ainda não há gateway integrado nesta fase,
    gerar as linhas de Fatura_Mensalidade já no ato da assinatura não
    tem esse custo — a emissão da cobrança em si (Transacao_Gateway)
    é que fica para quando o gateway existir.
    """
    __tablename__ = "contrato_financeiro"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("responsavel_financeiro_legal.id", ondelete="RESTRICT"), nullable=False)

    valor_total_anual: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantidade_parcelas: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    dia_vencimento_padrao: Mapped[int] = mapped_column(Integer, nullable=False, default=5)  # 1-28
    percentual_desconto_bolsa: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Um aluno só tem um contrato financeiro ativo por matrícula —
        # renegociações/reemissões passam por outra matrícula (novo ano
        # letivo) ou seriam tratadas como alteração deste registo.
        UniqueConstraint("matricula_id", name="uq_contrato_financeiro_matricula"),
    )


class FaturaMensalidade(Base):
    """Cada parcela individual (ex: "3/12") gerada a partir de um Contrato_Financeiro.

    status_pagamento reflete só o que já foi confirmado (PAGO) ou
    decidido manualmente (CANCELADO, NEGOCIADO) — "ATRASADO" nunca é
    escrito aqui por um job de fundo (RN02): é calculado em tempo real
    a partir de data_vencimento sempre que a fatura é consultada,
    exatamente como o documento pede.
    """
    __tablename__ = "fatura_mensalidade"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    contrato_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrato_financeiro.id", ondelete="CASCADE"), nullable=False)

    numero_parcela: Mapped[int] = mapped_column(Integer, nullable=False)  # Ex: 3 (de 3/12)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    status_pagamento: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE")  # PENDENTE, PAGO, CANCELADO, NEGOCIADO ("ATRASADO" é calculado, nunca gravado)

    data_pagamento_realizado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valor_pago_realizado: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    forma_pagamento: Mapped[str | None] = mapped_column(String(30), nullable=True)  # Preenchido ao marcar como pago; substitui Transacao_Gateway enquanto não há gateway real

    # Régua de cobrança (RN04) — para não reenviar o mesmo lembrete todos os dias.
    lembrete_previo_enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lembrete_vencimento_enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aviso_atraso_enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("contrato_id", "numero_parcela", name="uq_fatura_contrato_parcela"),
    )
