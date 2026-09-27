"""Schemas Pydantic partilhados entre módulos — o envelope de paginação
devolvido por app/core/paginacao.py::paginar(), e o tipo DecimalComoFloat
usado em todo response_model= que devolve um campo Decimal do ORM."""
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, PlainSerializer

T = TypeVar("T")

# Por omissão, o Pydantic v2 serializa Decimal para JSON como STRING
# ("500.00"), não como número — diferente do que jsonable_encoder fazia
# implicitamente antes de existir response_model= (convertia para
# float). O frontend Angular espera sempre `number` nestes campos (ver
# ex.: store/crm/crm.models.ts::OportunidadeCRM.valor_estimado_anual) —
# por isso todo response_model= com um campo Decimal do ORM usa este
# tipo em vez de Decimal puro, para manter o contrato JSON inalterado.
DecimalComoFloat = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]


class PaginaOut(BaseModel, Generic[T]):
    model_config = {"from_attributes": True}
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MensagemOut(BaseModel):
    """Resposta de uma ação que só confirma sucesso em texto — usada
    onde a rota devolvia antes um objeto ORM completo (não consumido
    pelo frontend) só para poder incluir esta mensagem."""
    mensagem: str
