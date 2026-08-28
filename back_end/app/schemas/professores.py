"""Schemas Pydantic de Professores e Alocação (Professor <-> Turma <-> Disciplina)."""
from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid

from app.core.validacao import validar_forca_senha


class ProfessorCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    palavra_passe: str = Field(..., min_length=8)
    formacao_academica: str | None = None

    _validar_palavra_passe = field_validator("palavra_passe")(validar_forca_senha)


class AlocacaoCreate(BaseModel):
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
