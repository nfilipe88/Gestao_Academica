"""Eventos de segurança — ver app/core/eventos_seguranca.py."""
from datetime import datetime
import uuid

from pydantic import BaseModel


class EventoSegurancaOut(BaseModel):
    id: uuid.UUID
    data_evento: datetime
    tipo: str
    gravidade: str
    ip: str
    user_agent: str | None
    email: str | None
    metodo: str | None
    caminho: str | None
    detalhe: str | None
    tenant_id: uuid.UUID | None
    # Só preenchido na vista do Super Admin (várias escolas).
    nome_escola: str | None = None


class BloqueioIpOut(BaseModel):
    ip: str
    ate: datetime
    motivo: str
