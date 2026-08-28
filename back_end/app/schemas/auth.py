from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid

from app.core.validacao import validar_forca_senha

class RegistoInicial(BaseModel):
    # Dados da Escola (Tenant)
    nome_fantasia: str = Field(..., example="Colégio do Futuro")
    nif: str = Field(..., example="501234567")

    # Dados do Gestor (Utilizador)
    nome_gestor: str = Field(..., example="João Silva")
    email_gestor: EmailStr = Field(..., example="joao.silva@colegiofuturo.pt")
    palavra_passe: str = Field(..., min_length=8, example="SenhaSegura123!")

    _validar_palavra_passe = field_validator("palavra_passe")(validar_forca_senha)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    utilizador: dict


class RefreshTokenIn(BaseModel):
    refresh_token: str


class RefreshTokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class LogoutIn(BaseModel):
    # Opcional: o front-end envia sempre que o tiver, mas um logout com
    # o access token já sem refresh_token à mão (ex.: apagado à parte)
    # continua a revogar pelo menos esse token.
    refresh_token: str | None = None


class EsqueciSenhaIn(BaseModel):
    email: EmailStr = Field(..., example="joao.silva@colegiofuturo.pt")


class RedefinirSenhaIn(BaseModel):
    token: str
    nova_senha: str = Field(..., min_length=8, example="SenhaNovaSegura123!")

    _validar_nova_senha = field_validator("nova_senha")(validar_forca_senha)
