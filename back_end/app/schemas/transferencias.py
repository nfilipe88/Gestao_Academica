import uuid

from pydantic import BaseModel


class SolicitacaoTransferenciaCreate(BaseModel):
    aluno_id: uuid.UUID
    nif_destino: str
    motivo: str | None = None


class RejeitarTransferenciaRequest(BaseModel):
    observacoes: str
