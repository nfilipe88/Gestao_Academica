"""Schema Pydantic de Notificacao — a mesma forma tanto para a listagem
(cruds/notificacoes.py::_serializar, já um dict à mão) como para
marcar_como_lida (devolve o ORM completo, mas só estes campos importam
ao sino: tenant_id/usuario_id/data_leitura nunca são lidos pelo
frontend, ver notificacoes-sino.component.ts)."""
from datetime import datetime
import uuid

from pydantic import BaseModel


class NotificacaoOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tipo: str
    titulo: str
    mensagem: str
    link: str | None = None
    lida: bool
    data_criacao: datetime
