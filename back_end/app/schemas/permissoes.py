"""Schemas Pydantic do Mapa de Permissões (ver models_permissoes.py)."""
import uuid

from pydantic import BaseModel, Field


class PermissaoModuloOut(BaseModel):
    id: uuid.UUID
    ordem: int
    modulo: str
    perfil: str
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool
    # Teto do código: o que as rotas deste módulo deixam este perfil fazer —
    # o mapa só restringe, nunca dá acima disto (ver core/mapa_permissoes.py).
    codigo_pode_criar: bool = True
    codigo_pode_ler: bool = True
    codigo_pode_atualizar: bool = True
    codigo_pode_apagar: bool = True
    # Linha sem rotas associadas (ex.: Visão Geral) — só descreve, não decide nada.
    informativo: bool = False
    # Operações que nunca se podem tirar (ex.: o Gestor nas Configurações).
    protegidas: list[str] = []
    # Só na vista do Gestor: o que vale na escola dele (mapa base E restrições da escola).
    escola_pode_criar: bool | None = None
    escola_pode_ler: bool | None = None
    escola_pode_atualizar: bool | None = None
    escola_pode_apagar: bool | None = None

    class Config:
        from_attributes = True


class PermissaoModuloUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool


class PerfilNomeOut(BaseModel):
    codigo: str
    nome: str
    model_config = {"from_attributes": True}


class PerfilNomeUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str = Field(..., min_length=2, max_length=60)
