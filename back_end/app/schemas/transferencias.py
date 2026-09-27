import uuid

from pydantic import BaseModel


class SolicitacaoTransferenciaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    aluno_id: uuid.UUID
    nif_destino: str
    motivo: str | None = None


class RejeitarTransferenciaRequest(BaseModel):
    model_config = {"extra": "forbid"}
    observacoes: str
