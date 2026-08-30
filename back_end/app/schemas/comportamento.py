"""Schemas Pydantic de Registos de Comportamento — ver app/database/models_diario.py::RegistroComportamento."""
from datetime import date
from pydantic import BaseModel
import uuid


class RegistroComportamentoCreate(BaseModel):
    tipo: str  # POSITIVO, NEGATIVO
    descricao: str
    data_ocorrencia: date | None = None  # None = hoje
    disciplina_id: uuid.UUID | None = None
