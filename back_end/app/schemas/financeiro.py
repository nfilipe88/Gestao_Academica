"""Schemas Pydantic do Financeiro (Contrato, Fatura, Gateway PayPal, Despesas)."""
from pydantic import BaseModel, model_validator
from datetime import date
from decimal import Decimal
import uuid


class ContratoCreate(BaseModel):
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
    valor_pago: Decimal | None = None  # se omitido, assume o valor atualizado (com juros/multa, se houver)
    forma_pagamento: str = "MANUAL"


class GerarCobrancaRequest(BaseModel):
    metodo_pagamento: str = "PAYPAL"


class CapturarPagamentoRequest(BaseModel):
    order_id: str


CATEGORIAS_DESPESA_VALIDAS = {"SALARIOS", "RENDA", "MATERIAL", "MANUTENCAO", "SERVICOS", "OUTRO"}


class DespesaCreate(BaseModel):
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
