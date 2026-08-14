"""Schemas Pydantic do Painel Super Admin."""
from pydantic import BaseModel


class TenantStatusUpdate(BaseModel):
    status: str  # ATIVO, SUSPENSO
