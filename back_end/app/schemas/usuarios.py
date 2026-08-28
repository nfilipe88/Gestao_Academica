"""Schemas Pydantic da Gestão de Acessos (RBAC) — ver cruds/usuarios.py."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid

from app.core.validacao import validar_forca_senha


class UsuarioListadoOut(BaseModel):
    id: uuid.UUID
    nome_completo: str
    email: str
    perfil_acesso: str
    ativo: bool
    data_criacao: datetime
    model_config = {"from_attributes": True}


class SecretariaCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    palavra_passe: str = Field(..., min_length=8)

    _validar_palavra_passe = field_validator("palavra_passe")(validar_forca_senha)


class PerfilAcessoUpdate(BaseModel):
    perfil_acesso: str  # GESTOR ou SECRETARIA — ver PERFIS_SEM_SUBTABELA em cruds/usuarios.py


class AtivoUpdate(BaseModel):
    ativo: bool


class UsuarioAuditoriaOut(BaseModel):
    id: uuid.UUID
    usuario_alvo_id: uuid.UUID
    nome_alvo: str
    nome_autor: str | None
    acao: str
    perfil_anterior: str | None
    perfil_novo: str | None
    detalhe: str | None
    data_acao: datetime
