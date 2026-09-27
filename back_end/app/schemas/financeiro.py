"""Schemas Pydantic do Financeiro (Contrato, Fatura, Gateway PayPal, Despesas)."""
from pydantic import BaseModel, model_validator
from datetime import date, datetime
from decimal import Decimal
import uuid

from app.schemas.comum import DecimalComoFloat


class ContratoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    matricula_id: uuid.UUID
    responsavel_id: uuid.UUID
    valor_total_anual: Decimal
    quantidade_parcelas: int = 12
    dia_vencimento_padrao: int = 5
    percentual_desconto_bolsa: Decimal = Decimal("0.00")
    mes_primeira_parcela: int | None = None  # 1-12; default: mês seguinte a hoje
    # Encargo único cobrado uma vez à assinatura do contrato, à parte das
    # `quantidade_parcelas` mensalidades — None/0 = sem taxa de matrícula.
    # Gerada como a parcela nº 0 do contrato (ver cruds/financeiro.py::criar_contrato).
    valor_taxa_matricula: Decimal | None = None


class FaturaMarcarPago(BaseModel):
    model_config = {"extra": "forbid"}
    valor_pago: Decimal | None = None  # se omitido, assume o valor atualizado (com juros/multa, se houver)
    forma_pagamento: str = "MANUAL"


class FaturaReportarPagamento(BaseModel):
    """Auto-relato do Responsável ("já efetuei a transferência") — ver
    cruds/financeiro.py::reportar_pagamento_fatura."""
    model_config = {"extra": "forbid"}
    referencia: str | None = None


class GerarCobrancaRequest(BaseModel):
    model_config = {"extra": "forbid"}
    metodo_pagamento: str = "PAYPAL"


class CapturarPagamentoRequest(BaseModel):
    model_config = {"extra": "forbid"}
    order_id: str


CATEGORIAS_DESPESA_VALIDAS = {"SALARIOS", "RENDA", "MATERIAL", "MANUTENCAO", "SERVICOS", "OUTRO"}


class DespesaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    categoria: str
    descricao: str
    valor: Decimal
    data_despesa: date
    forma_pagamento: str | None = None

    @model_validator(mode="after")
    def _validar(self):
        if self.categoria not in CATEGORIAS_DESPESA_VALIDAS:
            raise ValueError(f"categoria inválida. Use uma de: {', '.join(sorted(CATEGORIAS_DESPESA_VALIDAS))}.")
        if not self.descricao.strip():
            raise ValueError("descricao é obrigatória.")
        if self.valor <= 0:
            raise ValueError("valor tem de ser maior que zero.")
        return self


class ContratoFinanceiroOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    matricula_id: uuid.UUID
    responsavel_id: uuid.UUID
    valor_total_anual: DecimalComoFloat
    quantidade_parcelas: int
    dia_vencimento_padrao: int
    percentual_desconto_bolsa: DecimalComoFloat
    data_criacao: datetime
