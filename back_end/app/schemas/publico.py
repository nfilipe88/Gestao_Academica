"""Schemas do site público (landing, preços, contacto) — sem autenticação.
Ver app/api/v1/publico.py.
"""
from decimal import Decimal
from pydantic import BaseModel
import uuid

from app.schemas.admin import PlanoSaaSModuloOut


class ConfigPublicaOut(BaseModel):
    """Só valores seguros para expor ao frontend sem autenticação — a
    chave pública do reCAPTCHA v3 (ver core/recaptcha.py), nunca a
    RECAPTCHA_SECRET_KEY. None quando não está configurada (dev/testes),
    e o frontend simplesmente não pede token nenhum nesse caso."""
    recaptcha_site_key: str | None


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
