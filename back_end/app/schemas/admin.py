"""Schemas Pydantic do Painel Super Admin."""
from datetime import date

from pydantic import BaseModel


class TenantStatusUpdate(BaseModel):
    status: str  # ATIVO, SUSPENSO


class ValidadeLicencaUpdate(BaseModel):
    data_validade_licenca: date | None = None
