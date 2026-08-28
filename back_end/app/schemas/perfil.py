"""
Área de Perfil (self-service) — o próprio utilizador vê/edita o seu
registo e muda a sua palavra-passe. Ver app/cruds/perfil.py.

Distinto de app/schemas/usuarios.py (Gestão de Acessos): aquele é o
Gestor a gerir OUTRAS contas da escola; este é qualquer utilizador
autenticado (GESTOR/SECRETARIA/PROFESSOR/ALUNO/RESPONSAVEL/SUPER_ADMIN)
a gerir a PRÓPRIA conta — nunca recebe um usuario_id, o alvo é sempre
"quem está autenticado".
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid

from app.core.validacao import validar_forca_senha


class PerfilOut(BaseModel):
    id: uuid.UUID
    nome_completo: str
    email: str
    perfil_acesso: str
    tenant_id: uuid.UUID
    nome_instituicao: str
    data_criacao: datetime
    model_config = {"from_attributes": True}


class PerfilUpdate(BaseModel):
    nome_completo: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class AlterarSenhaIn(BaseModel):
    senha_atual: str
    nova_senha: str = Field(..., min_length=8)

    _validar_nova_senha = field_validator("nova_senha")(validar_forca_senha)
