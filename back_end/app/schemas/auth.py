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

    # Token do Google reCAPTCHA v3 (ver core/recaptcha.py) — opcional no
    # schema porque só é exigido quando RECAPTCHA_SECRET_KEY está
    # configurada no backend; em dev/testes sem essa chave, o campo é
    # ignorado.
    recaptcha_token: str | None = None

    # Tem de vir True — ver app/core/privacidade.py::VERSAO_TERMOS.
    aceitou_termos: bool = False

    _validar_palavra_passe = field_validator("palavra_passe")(validar_forca_senha)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    utilizador: dict


class RefreshTokenIn(BaseModel):
    # Opcional: o browser envia-o no cookie HttpOnly (ver api/v1/auth.py); clientes
    # de API continuam a poder mandá-lo no corpo.
    refresh_token: str | None = None


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


class AtivarContaIn(BaseModel):
    token: str
