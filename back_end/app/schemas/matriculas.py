"""Schemas Pydantic de Matrículas."""
from datetime import datetime
import uuid

from pydantic import BaseModel


class MatriculaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    ano_letivo: int


class MatriculaStatusUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    status_matricula: str
    motivo: str | None = None


class MatriculaOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    ano_letivo: int
    status_matricula: str
    motivo: str | None = None
    data_matricula: datetime
    resultado_final: str | None = None
    resultado_detalhe: dict | None = None
    resultado_em: datetime | None = None
