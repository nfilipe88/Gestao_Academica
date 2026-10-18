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
    # Só diz SE há assinatura pessoal ativa — a imagem sai por GET
    # /perfil/assinatura (ver app/api/v1/perfil.py), nunca embutida aqui.
    tem_assinatura_pessoal: bool = False
    dois_fatores_ativo: bool = False
    model_config = {"from_attributes": True}


class PerfilUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    nome_completo: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    # Obrigatória só quando o email muda (ver cruds/perfil.py::atualizar_perfil):
    # o email é o identificador de login e o destino da recuperação de
    # palavra-passe — quem tivesse só uma sessão aberta (computador
    # partilhado, token roubado) não pode desviá-lo para si.
    senha_atual: str | None = Field(None, max_length=128)


class AlterarSenhaIn(BaseModel):
    model_config = {"extra": "forbid"}
    senha_atual: str = Field(..., max_length=128)
    nova_senha: str = Field(..., min_length=8, max_length=128)

    _validar_nova_senha = field_validator("nova_senha")(validar_forca_senha)


class AlterarSenhaOut(BaseModel):
    mensagem: str
    # Todas as sessões anteriores são terminadas ao mudar a palavra-passe,
    # incluindo a atual — este é o token novo com que ela continua.
    access_token: str
    token_type: str = "bearer"


class ConfirmarSenhaIn(BaseModel):
    """Ligar/desligar a verificação em dois passos exige a palavra-passe
    atual — mesma razão da mudança de e-mail (ver PerfilUpdate)."""
    model_config = {"extra": "forbid"}
    senha_atual: str = Field(..., max_length=128)


class AtivarDoisFatoresOut(BaseModel):
    desafio: str
    email_mascarado: str


class ConfirmarDoisFatoresIn(BaseModel):
    model_config = {"extra": "forbid"}
    desafio: str = Field(..., min_length=10, max_length=100)
    codigo: str = Field(..., pattern=r"^\s*\d{6}\s*$")
