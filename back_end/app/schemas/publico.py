"""Schemas do site público (landing, preços, contacto) — sem autenticação.
Ver app/api/v1/publico.py.
"""
from decimal import Decimal
from pydantic import BaseModel
import uuid

from app.schemas.admin import PlanoSaaSModuloOut


class PlanoSaaSPublicoOut(BaseModel):
    """Igual a PlanoSaaSOut (app/schemas/admin.py) mas sem `ativo` — a
    lista pública já só devolve planos ativos, o campo seria sempre
    True e não diz nada a um visitante."""
    id: uuid.UUID
    nome: str
    preco_por_aluno: Decimal
    limite_alunos: int | None
    descricao: str | None
    dias_periodo_teste: int
    modulos: list[PlanoSaaSModuloOut] = []

    model_config = {"from_attributes": True}
