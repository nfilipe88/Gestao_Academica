import uuid
from datetime import time

from pydantic import BaseModel, field_validator

# Moedas efetivamente aceites pela PayPal Orders API (lista oficial,
# ISO 4217) — restringir a estas evita que uma escola escolha uma moeda
# "de exibição" que depois falha silenciosamente ao gerar uma cobrança
# PayPal (ex.: AOA/Kwanza não está nesta lista e nunca vai funcionar).
MOEDAS_SUPORTADAS = {
    "AUD", "BRL", "CAD", "CNY", "CZK", "DKK", "EUR", "HKD", "HUF", "ILS",
    "JPY", "MYR", "MXN", "TWD", "NZD", "NOK", "PHP", "PLN", "GBP", "SGD",
    "SEK", "CHF", "THB", "USD",
}


class ConfiguracaoTenantOut(BaseModel):
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
