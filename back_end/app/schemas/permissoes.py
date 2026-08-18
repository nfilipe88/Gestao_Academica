"""Schemas Pydantic do Mapa de Permissões (ver models_permissoes.py)."""
import uuid

from pydantic import BaseModel


class PermissaoModuloOut(BaseModel):
    id: uuid.UUID
    ordem: int
    modulo: str
    perfil: str
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool

    class Config:
        from_attributes = True


class PermissaoModuloUpdate(BaseModel):
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool
