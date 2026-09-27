"""Schemas Pydantic de Alunos, Responsáveis e o vínculo entre eles."""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date, datetime
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


class AlunoOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID | None = None
    matricula_interna: str
    nome_completo: str
    data_nascimento: date
    numero_documento: str | None = None
    data_criacao: datetime
    ativo: bool


class AlunoListItemOut(AlunoOut):
    """Mesmos campos de AlunoOut, mais a contagem de responsáveis
    vinculados que listar_alunos() calcula à parte (ver cruds/alunos.py) —
    não vem do ORM, por isso não pode ficar só em AlunoOut."""
    num_responsaveis: int


class ResponsavelFinanceiroLegalOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID | None = None
    nome_completo: str
    numero_documento: str | None = None
    telefone_contato: str
    email: str | None = None
    data_criacao: datetime


class AlunoResponsavelOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    aluno_id: uuid.UUID
    responsavel_id: uuid.UUID
    tipo_parentesco: str
    responsavel_financeiro: bool
