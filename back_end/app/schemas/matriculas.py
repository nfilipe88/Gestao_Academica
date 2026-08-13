"""Schemas Pydantic de Matrículas."""
from pydantic import BaseModel
import uuid


class MatriculaCreate(BaseModel):
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    ano_letivo: int


class MatriculaStatusUpdate(BaseModel):
    status_matricula: str
    motivo: str | None = None
