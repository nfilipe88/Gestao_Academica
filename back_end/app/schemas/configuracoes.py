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

    @field_validator("moeda")
    @classmethod
    def validar_moeda(cls, valor: str) -> str:
        valor = (valor or "").strip().upper()
        if valor not in MOEDAS_SUPORTADAS:
            raise ValueError(f"Moeda inválida. Use uma de: {', '.join(sorted(MOEDAS_SUPORTADAS))}.")
        return valor
