import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
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
        # Cobre a query mais pesada desta tabela: a régua de cobrança
        # diária (RN04, ver cruds/financeiro.py::processar_regua_cobranca_do_tenant)
        # varre TODAS as faturas PENDENTE de uma escola, todos os dias,
        # para todas as escolas ATIVAS — sem isto, sequential scan
        # completo à tabela em cada execução do job.
        Index("ix_fatura_tenant_status", "tenant_id", "status_pagamento"),
    )


class ContadorRecibo(Base):
    """Contador de numeração sequencial de recibos, por escola e ano.

    Legislação fiscal (ex.: regime angolano de faturação, sob a AGT)
    exige que a numeração de documentos de venda/recibo seja sequencial
    e sem falhas nem repetições dentro de uma série — nunca "saltar" um
    número nem reutilizá-lo, mesmo que o registo correspondente seja
    depois anulado. Uma linha aqui por (tenant, ano), bloqueada com
    SELECT...FOR UPDATE (ver cruds/financeiro.py::_proximo_numero_recibo)
    antes de emitir cada Recibo, garante isso mesmo com pedidos
    concorrentes — sem isto, dois pagamentos confirmados ao mesmo
    tempo podiam ler o "próximo número" igual e emitir dois recibos com
    o mesmo número.
    """
    __tablename__ = "contador_recibo"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), primary_key=True)
    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    proximo_numero: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Recibo(Base):
    """Recibo de pagamento de uma Fatura_Mensalidade.

    IMPORTANTE — isto não é uma "Fatura" no sentido fiscal certificado
    (em Angola, isso exige o software de faturação estar certificado
    pela AGT — Administração Geral Tributária —, um processo legal e
    de registo, não algo que se resolva só com código). É o
    comprovativo técnico de que um pagamento foi recebido, já com os
    dados que esse processo de certificação exigiria preparados
    (numeração sequencial sem falhas via ContadorRecibo, NIF/documento
    de quem paga, NIF da escola) — a base para pedir a certificação
    mais tarde, não a certificação em si.
    """
    __tablename__ = "recibo"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    fatura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fatura_mensalidade.id", ondelete="CASCADE"), nullable=False)

    numero_sequencial: Mapped[int] = mapped_column(Integer, nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    data_emissao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False)
    forma_pagamento: Mapped[str] = mapped_column(String(30), nullable=False)

    # Fotografia do momento da emissão — mesmo que o Responsável mude o
    # nome/documento depois, o recibo já emitido não pode mudar com ele.
    nome_pagador: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_documento_pagador: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("fatura_id", name="uq_recibo_fatura"),
        UniqueConstraint("tenant_id", "ano", "numero_sequencial", name="uq_recibo_tenant_ano_numero"),
    )


class TransacaoGateway(Base):
    """
    Regista cada tentativa de cobrança feita junto de um gateway externo
    para uma Fatura_Mensalidade (RN03 do documento). Por agora só existe
    o método PAYPAL — o campo é uma string livre (não Enum) para não
    exigir migração de esquema quando outros métodos forem adicionados
    (ex: Referência Multibanco via ifthenpay).

    Uma fatura pode ter várias transações ao longo do tempo (ex: uma
    tentativa expirou/cancelou e o responsável gerou outra) — por isso
    não há UniqueConstraint em fatura_id; a idempotência "não crie uma
    segunda cobrança em aberto" é responsabilidade do endpoint
    (POST /financeiro/faturas/{id}/gerar-cobranca), não do esquema.
    """
    __tablename__ = "transacao_gateway"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    fatura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fatura_mensalidade.id", ondelete="CASCADE"), nullable=False)

    metodo_pagamento: Mapped[str] = mapped_column(String(30), nullable=False)  # PAYPAL (por agora)
    gateway_transaction_id: Mapped[str] = mapped_column(String(100), nullable=False)  # id da Order no PayPal
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="AGUARDANDO_PAGAMENTO")
    # AGUARDANDO_PAGAMENTO, PAGO, CANCELADO, EXPIRADO

    dados_cobranca: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # approve_url, capture_id, payload bruto relevante
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class Despesa(Base):
    """Uma saída financeira da escola (salários, renda, material,
    manutenção, serviços…), lançada manualmente pela Secretaria/Gestor.

    Contrapartida das Entradas (Fatura_Mensalidade paga) para as
    Estatísticas financeiras (ver app/cruds/estatisticas.py) — sem
    isto, "maiores saídas"/"meses com mais despesas" não tinham
    nenhum dado real na plataforma. Deliberadamente simples (sem
    workflow de aprovação, sem anexos, sem recorrência automática):
    um registo manual do que já foi pago, não um sistema de gestão de
    despesas completo.
    """
    __tablename__ = "despesa"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    categoria: Mapped[str] = mapped_column(String(30), nullable=False)  # SALARIOS, RENDA, MATERIAL, MANUTENCAO, SERVICOS, OUTRO
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_despesa: Mapped[date] = mapped_column(Date, nullable=False)
    forma_pagamento: Mapped[str | None] = mapped_column(String(30), nullable=True)  # mesmo conjunto de FaturaMensalidade.forma_pagamento

    criado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Consulta mais pesada desta tabela: relatório de Estatísticas
        # filtrado por intervalo de datas, por escola.
        Index("ix_despesa_tenant_data", "tenant_id", "data_despesa"),
    )
