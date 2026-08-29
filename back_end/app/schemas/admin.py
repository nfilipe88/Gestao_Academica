"""Schemas Pydantic do Painel Super Admin."""
from datetime import date
from decimal import Decimal
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.validacao import validar_forca_senha


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

    _validar_palavra_passe = field_validator("palavra_passe")(validar_forca_senha)


# ==========================================
# SAAS BILLING — Planos e Assinaturas
# ==========================================
class PlanoSaaSModuloInput(BaseModel):
    """Um módulo incluído no plano — ver app.core.modulos.MODULOS_GATEAVEIS
    para os nomes válidos (têm de corresponder exatamente aos usados no
    Mapa de Permissões)."""
    modulo: str
    preco_adicional: Decimal = Decimal("0.00")


class PlanoSaaSModuloOut(PlanoSaaSModuloInput):
    model_config = {"from_attributes": True}


class PlanoSaaSCreate(BaseModel):
    nome: str
    preco_por_aluno: Decimal
    limite_alunos: int | None = None
    descricao: str | None = None
    # 0 = sem período de teste (cobrança normal desde o início).
    dias_periodo_teste: int = 0
    # Módulos incluídos neste plano — um módulo AUSENTE daqui fica
    # bloqueado para as escolas deste plano (ver app/core/modulos.py).
    # Substitui sempre a lista anterior por completo (não é um PATCH
    # incremental) — mais simples e previsível do que "adicionar"/
    # "remover" módulos um a um.
    modulos: list[PlanoSaaSModuloInput] = []

    @model_validator(mode="after")
    def _validar(self):
        from app.core.modulos import MODULOS_GATEAVEIS

        if not self.nome.strip():
            raise ValueError("nome é obrigatório.")
        if self.preco_por_aluno < 0:
            raise ValueError("preco_por_aluno não pode ser negativo.")
        if self.limite_alunos is not None and self.limite_alunos <= 0:
            raise ValueError("limite_alunos, se definido, tem de ser maior que zero.")
        if self.dias_periodo_teste < 0:
            raise ValueError("dias_periodo_teste não pode ser negativo.")
        nomes_vistos = set()
        for m in self.modulos:
            if m.modulo not in MODULOS_GATEAVEIS:
                raise ValueError(f'"{m.modulo}" não é um módulo válido. Use um de: {", ".join(sorted(MODULOS_GATEAVEIS))}.')
            if m.modulo in nomes_vistos:
                raise ValueError(f'Módulo "{m.modulo}" repetido na lista.')
            nomes_vistos.add(m.modulo)
            if m.preco_adicional < 0:
                raise ValueError(f'O preço adicional de "{m.modulo}" não pode ser negativo.')
        return self


class PlanoSaaSUpdate(PlanoSaaSCreate):
    ativo: bool = True


class PlanoSaaSOut(BaseModel):
    id: uuid.UUID
    nome: str
    preco_por_aluno: Decimal
    limite_alunos: int | None
    descricao: str | None
    dias_periodo_teste: int
    ativo: bool
    modulos: list[PlanoSaaSModuloOut] = []

    model_config = {"from_attributes": True}


class AssinaturaTenantInput(BaseModel):
    plano_id: uuid.UUID
    proxima_cobranca: date
