"""Schema de leitura da trilha de auditoria geral — ver app/cruds/auditoria.py."""
from datetime import datetime
from pydantic import BaseModel
import uuid


class AuditLogOut(BaseModel):
    id: uuid.UUID
    autor_id: uuid.UUID | None
    autor_nome: str | None
    autor_perfil: str | None
    acao: str
    entidade: str
    entidade_id: str
    alteracoes: dict | None
    criado_em: datetime
