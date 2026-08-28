import uuid
from datetime import time

from pydantic import BaseModel, field_validator

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
    periodo_manha_inicio: time | None = None
    periodo_manha_fim: time | None = None
    periodo_tarde_inicio: time | None = None
    periodo_tarde_fim: time | None = None
    periodo_pos_laboral_inicio: time | None = None
    periodo_pos_laboral_fim: time | None = None

    @field_validator("moeda")
    @classmethod
    def validar_moeda(cls, valor: str) -> str:
        valor = (valor or "").strip().upper()
        if valor not in MOEDAS_SUPORTADAS:
            raise ValueError(f"Moeda inválida. Use uma de: {', '.join(sorted(MOEDAS_SUPORTADAS))}.")
        return valor

    @field_validator(
        "periodo_manha_inicio", "periodo_manha_fim", "periodo_tarde_inicio",
        "periodo_tarde_fim", "periodo_pos_laboral_inicio", "periodo_pos_laboral_fim",
        mode="before"
    )
    @classmethod
    def _vazio_para_none(cls, valor):
        # O <input type="time"> do frontend envia "" quando fica vazio —
        # Pydantic não aceita "" como time, tem de virar None explicitamente.
        return None if valor == "" else valor


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
