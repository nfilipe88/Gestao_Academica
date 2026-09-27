"""Schemas Pydantic de Matrículas."""
from pydantic import BaseModel
import uuid


class MatriculaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    ano_letivo: int


class MatriculaStatusUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    status_matricula: str
    motivo: str | None = None
