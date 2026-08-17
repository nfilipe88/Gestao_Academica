from pydantic import BaseModel, EmailStr, Field
import uuid

class RegistoInicial(BaseModel):
    # Dados da Escola (Tenant)
    nome_fantasia: str = Field(..., example="Colégio do Futuro")
    nif: str = Field(..., example="501234567")

    # Dados do Gestor (Utilizador)
    nome_gestor: str = Field(..., example="João Silva")
    email_gestor: EmailStr = Field(..., example="joao.silva@colegiofuturo.pt")
    palavra_passe: str = Field(..., min_length=8, example="SenhaSegura123!")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    utilizador: dict


class EsqueciSenhaIn(BaseModel):
    email: EmailStr = Field(..., example="joao.silva@colegiofuturo.pt")


class RedefinirSenhaIn(BaseModel):
    token: str
    nova_senha: str = Field(..., min_length=8, example="SenhaNovaSegura123!")
