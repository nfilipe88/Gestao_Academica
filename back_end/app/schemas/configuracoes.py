import re
import uuid
from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

# "2026/2027" — ano de início e ano de fim, cada um com 4 dígitos. Ver
# Tenant.ano_letivo_atual: pedido explícito do utilizador para o campo
# Ano Letivo ser sempre esta junção, nunca só o ano de início solto
# (que é a convenção usada, à parte, em Turma.ano_letivo/Matricula.ano_letivo).
_ANO_LETIVO_ATUAL_REGEX = re.compile(r"^\d{4}/\d{4}$")

# Moedas efetivamente aceites pela PayPal Orders API (lista oficial,
# ISO 4217) — usada só para validar quando se está mesmo a gerar uma
# cobrança PayPal (ver cruds/financeiro.py::gerar_cobranca), nunca para
# restringir a moeda de exibição/cobrança da escola em si (essa é
# MOEDAS_SUPORTADAS, abaixo) — as duas listas eram a mesma até esta
# escola precisar de funcionar em Angola: o Kwanza (AOA) é uma moeda
# real e válida para a escola cobrar, só não é uma que o PayPal aceite.
MOEDAS_PAYPAL_SUPORTADAS = {
    "AUD", "BRL", "CAD", "CNY", "CZK", "DKK", "EUR", "HKD", "HUF", "ILS",
    "JPY", "MYR", "MXN", "TWD", "NZD", "NOK", "PHP", "PLN", "GBP", "SGD",
    "SEK", "CHF", "THB", "USD",
}

# Moedas que a escola pode escolher para os seus próprios preços/faturas
# — todas as que o PayPal aceita, mais as que não aceita mas continuam
# a ser moedas reais que uma escola precisa de cobrar (uma escola nessa
# moeda usa o pagamento manual/transferência em vez do botão PayPal,
# ver financeiro.component e gerar_cobranca).
MOEDAS_SUPORTADAS = MOEDAS_PAYPAL_SUPORTADAS | {"AOA"}


class ConfiguracaoTenantOut(BaseModel):
    iban: str | None = None
    moeda: str
    # Só diz SE há logótipo — o ficheiro em si sai por GET
    # /configuracoes/logotipo (download autenticado, ver
    # app/api/v1/configuracoes.py), nunca embutido aqui.
    tem_logotipo: bool = False
    telefone_contacto: str | None = None
    email_contacto: str | None = None
    morada: str | None = None
    cidade: str | None = None
    codigo_postal: str | None = None
    pais: str | None = None
    nota_minima_aprovacao: float | None = None
    # Nota máxima da escala de notas da escola (ex.: 10 ou 20) — ver
    # Tenant.nota_maxima. Sempre presente (coluna NOT NULL).
    nota_maxima: float
    # Valor padrão da taxa de matrícula (encargo único, distinto das
    # mensalidades) — None = escola não cobra. Ver Tenant.valor_taxa_matricula.
    valor_taxa_matricula: Decimal | None = None
    # Ano Letivo corrente — início/fim são as datas reais (regra geral,
    # início num ano e fim no seguinte); ano_letivo_atual é a junção
    # "YYYY/YYYY" dos dois anos (ex.: "2026/2027") — pedido explícito do
    # utilizador, distinto de propósito do inteiro solto usado em
    # Turma.ano_letivo/Matricula.ano_letivo. Ver
    # Tenant.data_inicio_ano_letivo/data_fim_ano_letivo/ano_letivo_atual.
    data_inicio_ano_letivo: date | None = None
    data_fim_ano_letivo: date | None = None
    ano_letivo_atual: str | None = None
    periodo_manha_inicio: time | None = None
    periodo_manha_fim: time | None = None
    periodo_tarde_inicio: time | None = None
    periodo_tarde_fim: time | None = None
    periodo_pos_laboral_inicio: time | None = None
    periodo_pos_laboral_fim: time | None = None

    model_config = {"from_attributes": True}


class ConfiguracaoTenantUpdate(BaseModel):
    iban: str | None = None
    moeda: str
    telefone_contacto: str | None = None
    email_contacto: str | None = None
    morada: str | None = None
    cidade: str | None = None
    codigo_postal: str | None = None
    pais: str | None = None
    nota_minima_aprovacao: float | None = None
    # Obrigatório (ao contrário de nota_minima_aprovacao, que é opcional)
    # — ver Tenant.nota_maxima para o porquê.
    nota_maxima: float
    valor_taxa_matricula: Decimal | None = None
    data_inicio_ano_letivo: date | None = None
    data_fim_ano_letivo: date | None = None
    ano_letivo_atual: str | None = None
    periodo_manha_inicio: time | None = None
    periodo_manha_fim: time | None = None
    periodo_tarde_inicio: time | None = None
    periodo_tarde_fim: time | None = None
    periodo_pos_laboral_inicio: time | None = None
    periodo_pos_laboral_fim: time | None = None

    @field_validator("nota_maxima")
    @classmethod
    def validar_nota_maxima(cls, valor: float) -> float:
        if valor <= 0:
            raise ValueError("A nota máxima tem de ser maior que zero.")
        return valor

    @field_validator("ano_letivo_atual")
    @classmethod
    def validar_ano_letivo_atual(cls, valor: str | None) -> str | None:
        if valor is not None and not _ANO_LETIVO_ATUAL_REGEX.match(valor):
            raise ValueError('O Ano Letivo tem de estar no formato "YYYY/YYYY" (ex.: 2026/2027).')
        return valor

    @field_validator("moeda")
    @classmethod
    def validar_moeda(cls, valor: str) -> str:
        valor = (valor or "").strip().upper()
        if valor not in MOEDAS_SUPORTADAS:
            raise ValueError(f"Moeda inválida. Use uma de: {', '.join(sorted(MOEDAS_SUPORTADAS))}.")
        return valor

    @field_validator("valor_taxa_matricula")
    @classmethod
    def validar_valor_taxa_matricula(cls, valor: Decimal | None) -> Decimal | None:
        if valor is not None and valor < 0:
            raise ValueError("O valor da taxa de matrícula não pode ser negativo.")
        return valor

    @field_validator(
        "periodo_manha_inicio", "periodo_manha_fim", "periodo_tarde_inicio",
        "periodo_tarde_fim", "periodo_pos_laboral_inicio", "periodo_pos_laboral_fim",
        "data_inicio_ano_letivo", "data_fim_ano_letivo", "ano_letivo_atual",
        mode="before"
    )
    @classmethod
    def _vazio_para_none(cls, valor):
        # O <input type="time"/"date"/"number"> do frontend envia "" quando
        # fica vazio — Pydantic não aceita "" nesses tipos, tem de virar
        # None explicitamente.
        return None if valor == "" else valor

    @model_validator(mode="after")
    def _validar_intervalo_ano_letivo(self) -> "ConfiguracaoTenantUpdate":
        # Mesmo padrão de validação de intervalo já usado em
        # cruds/estatisticas.py::obter_relatorio — só faz sentido
        # comparar quando as duas datas vêm preenchidas; uma escola a
        # meio de preencher (só uma das duas) não é bloqueada aqui.
        if self.data_inicio_ano_letivo and self.data_fim_ano_letivo and self.data_fim_ano_letivo <= self.data_inicio_ano_letivo:
            raise ValueError("A data de fim do ano letivo tem de ser posterior à data de início.")
        if self.nota_minima_aprovacao is not None and self.nota_minima_aprovacao > self.nota_maxima:
            raise ValueError("A nota mínima de aprovação não pode ser maior do que a nota máxima da escala.")
        return self


# ==========================================
# TIPOS DE AVALIAÇÃO (catálogo por escola)
# ==========================================
class TipoAvaliacaoOut(BaseModel):
    id: uuid.UUID
    nome: str
    requer_agendamento: bool
    ativo: bool

    model_config = {"from_attributes": True}


class TipoAvaliacaoCreate(BaseModel):
    nome: str
    requer_agendamento: bool = False


class TipoAvaliacaoUpdate(BaseModel):
    nome: str
    requer_agendamento: bool
    ativo: bool
