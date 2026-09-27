"""Schemas Pydantic de Alunos, Responsáveis e o vínculo entre eles."""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
import uuid

from app.core.validacao import validar_forca_senha


class AlunoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    matricula_interna: str
    nome_completo: str
    data_nascimento: date
    numero_documento: str | None = None


class AlunoAtivoUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    ativo: bool


class ResponsavelCreate(BaseModel):
    model_config = {"extra": "forbid"}
    nome_completo: str
    telefone_contato: str
    numero_documento: str | None = None
    email: str | None = None


class VincularResponsavel(BaseModel):
    model_config = {"extra": "forbid"}
    responsavel_id: uuid.UUID
    tipo_parentesco: str
    responsavel_financeiro: bool = False


class CriarAcessoRequest(BaseModel):
    """Concede login próprio (Portal do Aluno/Responsável) a um Aluno ou Responsável já cadastrado."""
    model_config = {"extra": "forbid"}
    email: EmailStr
    palavra_passe: str = Field(..., min_length=8)

    _validar_palavra_passe = field_validator("palavra_passe")(validar_forca_senha)
