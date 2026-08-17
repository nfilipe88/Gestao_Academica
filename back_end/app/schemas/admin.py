"""Schemas Pydantic do Painel Super Admin."""
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class TenantStatusUpdate(BaseModel):
    status: str  # ATIVO, SUSPENSO


class ValidadeLicencaUpdate(BaseModel):
    data_validade_licenca: date | None = None


class TenantCreateAdmin(BaseModel):
    """Criação de escola pelo Super Admin — ao contrário de POST /api/v1/auth/registo
    (auto-serviço, a própria escola regista-se), esta é a via de onboarding
    gatekeeping descrita no documento original: o Super Admin decide criar
    a conta em nome da escola (ex.: veio por contacto comercial direto)."""
    nome_fantasia: str = Field(..., example="Colégio do Futuro")
    nif: str = Field(..., example="501234567")
    nome_gestor: str = Field(..., example="João Silva")
    email_gestor: EmailStr = Field(..., example="joao.silva@colegiofuturo.pt")
    palavra_passe: str = Field(..., min_length=8, example="SenhaSegura123!")
