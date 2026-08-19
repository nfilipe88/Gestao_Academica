"""Schemas Pydantic da Tabela de Propinas (ver models_propinas.py)."""
import uuid
from decimal import Decimal

from pydantic import BaseModel, model_validator


class LinhaPropina(BaseModel):
    """Uma linha da tabela — sempre uma Série/Ano concreta, com ou sem
    valor definido ainda para o ano letivo pedido (propina_id=None ->
    esta série ainda não tem preço registado nesse ano)."""
    curso_id: uuid.UUID
    curso_nome: str
    serie_ano_id: uuid.UUID
    serie_ano_nome: str
    propina_id: uuid.UUID | None
    ano_letivo: int
    valor_mensalidade: Decimal | None
    valor_matricula: Decimal | None

    model_config = {"from_attributes": True}


class PropinaUpdate(BaseModel):
    ano_letivo: int
    valor_mensalidade: Decimal
    valor_matricula: Decimal | None = None

    @model_validator(mode="after")
    def _validar(self):
        if self.valor_mensalidade < 0:
            raise ValueError("valor_mensalidade não pode ser negativo.")
        if self.valor_matricula is not None and self.valor_matricula < 0:
            raise ValueError("valor_matricula não pode ser negativo.")
        return self
