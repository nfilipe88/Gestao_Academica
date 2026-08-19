"""Schemas Pydantic do Painel Super Admin."""
from datetime import date
from decimal import Decimal
import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator


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


# ==========================================
# SAAS BILLING — Planos e Assinaturas
# ==========================================
class PlanoSaaSCreate(BaseModel):
    nome: str
    preco_mensal: Decimal
    limite_alunos: int | None = None
    descricao: str | None = None
    # 0 = sem período de teste (cobrança normal desde o início).
    dias_periodo_teste: int = 0

    @model_validator(mode="after")
    def _validar(self):
        if not self.nome.strip():
            raise ValueError("nome é obrigatório.")
        if self.preco_mensal < 0:
            raise ValueError("preco_mensal não pode ser negativo.")
        if self.limite_alunos is not None and self.limite_alunos <= 0:
            raise ValueError("limite_alunos, se definido, tem de ser maior que zero.")
        if self.dias_periodo_teste < 0:
            raise ValueError("dias_periodo_teste não pode ser negativo.")
        return self


class PlanoSaaSUpdate(PlanoSaaSCreate):
    ativo: bool = True


class AssinaturaTenantInput(BaseModel):
    plano_id: uuid.UUID
    proxima_cobranca: date
