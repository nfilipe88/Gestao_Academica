"""Schemas Pydantic de Comunicados/Convocatórias."""
from pydantic import BaseModel
import uuid


class ComunicadoCreate(BaseModel):
    tipo: str
    titulo: str
    corpo: str
    destinatario_tipo: str
    destinatario_turma_id: uuid.UUID | None = None
    destinatario_aluno_id: uuid.UUID | None = None
