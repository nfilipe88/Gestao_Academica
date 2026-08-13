"""Schemas Pydantic de Professores e Alocação (Professor <-> Turma <-> Disciplina)."""
from pydantic import BaseModel, EmailStr, Field
import uuid


class ProfessorCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    palavra_passe: str = Field(..., min_length=8)
    formacao_academica: str | None = None


class AlocacaoCreate(BaseModel):
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
