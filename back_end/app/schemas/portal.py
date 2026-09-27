"""Schemas Pydantic específicos do Portal do Aluno/Responsável."""
from pydantic import BaseModel


class PedirTransferenciaRequest(BaseModel):
    model_config = {"extra": "forbid"}
    nif_destino: str
    motivo: str | None = None
