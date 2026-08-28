"""Schemas Pydantic de Comunicados/Convocatórias."""
from datetime import datetime
from pydantic import BaseModel
import uuid


class ComunicadoCreate(BaseModel):
    tipo: str
    titulo: str
    corpo: str
    destinatario_tipo: str
    destinatario_turma_id: uuid.UUID | None = None
    destinatario_aluno_id: uuid.UUID | None = None


class AnexoComunicacaoOut(BaseModel):
    id: uuid.UUID
    nome_original: str
    content_type: str
    tamanho_bytes: int
    criado_em: datetime

    model_config = {"from_attributes": True}
