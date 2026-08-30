"""Schemas Pydantic específicos do Portal do Aluno/Responsável."""
from pydantic import BaseModel


class PedirTransferenciaRequest(BaseModel):
    nif_destino: str
    motivo: str | None = None
