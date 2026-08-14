"""Schemas Pydantic de Alunos, Responsáveis e o vínculo entre eles."""
from pydantic import BaseModel, EmailStr, Field
from datetime import date
import uuid


class AlunoCreate(BaseModel):
    matricula_interna: str
    nome_completo: str
    data_nascimento: date
    numero_documento: str | None = None


class ResponsavelCreate(BaseModel):
    nome_completo: str
    telefone_contato: str
    numero_documento: str | None = None
    email: str | None = None


class VincularResponsavel(BaseModel):
    responsavel_id: uuid.UUID
    tipo_parentesco: str
    responsavel_financeiro: bool = False


class CriarAcessoRequest(BaseModel):
    """Concede login próprio (Portal do Aluno/Responsável) a um Aluno ou Responsável já cadastrado."""
    email: EmailStr
    palavra_passe: str = Field(..., min_length=8)
