"""Schemas do Suporte Virtual (chat de IA) e do sistema de tickets — ver
app/core/suporte_virtual.py e app/cruds/suporte.py."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field
import uuid

# ==========================================
# Suporte Virtual (chat de IA, sem BD)
# ==========================================

# Endpoint público e cada pedido é pago (API de IA) — sem estes tetos,
# um único pedido podia mandar centenas de milhares de tokens de
# "histórico" inventado. Folgados para nunca rejeitar uma conversa real
# (o servidor só usa as últimas mensagens, ver core/suporte_virtual.py).
_MAX_MENSAGENS_HISTORICO = 100
_MAX_CARACTERES_MENSAGEM = 4000


class MensagemChatSuporte(BaseModel):
    model_config = {"extra": "forbid"}
    papel: Literal["visitante", "assistente"]
    texto: str = Field(..., max_length=_MAX_CARACTERES_MENSAGEM)


class PerguntaSuporteVirtual(BaseModel):
    model_config = {"extra": "forbid"}
    historico: list[MensagemChatSuporte] = Field(default_factory=list, max_length=_MAX_MENSAGENS_HISTORICO)
    pergunta: str = Field(..., min_length=1, max_length=1000)


# ==========================================
# Tickets
# ==========================================

class TicketCreate(BaseModel):
    """Usado tanto pelo formulário público (/contacto, sem sessão) como
    pelo staff já autenticado — a rota autenticada ignora nome/email
    daqui e usa os do próprio utilizador (ver api/v1/suporte.py)."""
    model_config = {"extra": "forbid"}
    nome: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    assunto: str = Field(..., min_length=1, max_length=200)
    mensagem: str = Field(..., min_length=1, max_length=5000)


class TicketPublicoCreate(TicketCreate):
    """Formulário de Contacto do site público (sem sessão) — com o token
    do reCAPTCHA v3, tal como o registo de escola e a captação de leads
    (ver app/core/recaptcha.py)."""
    recaptcha_token: str | None = Field(None, max_length=4000)


class MensagemTicketCreate(BaseModel):
    model_config = {"extra": "forbid"}
    corpo: str = Field(..., min_length=1, max_length=5000)


class TicketEstadoUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    estado: str  # ABERTO, EM_ANDAMENTO, RESOLVIDO, FECHADO


class TicketMensagemOut(BaseModel):
    id: uuid.UUID
    autor_tipo: str
    autor_nome: str
    corpo: str
    criado_em: datetime
    model_config = {"from_attributes": True}


class TicketOut(BaseModel):
    id: uuid.UUID
    autor_nome: str
    autor_email: str
    assunto: str
    estado: str
    criado_em: datetime
    atualizado_em: datetime
    model_config = {"from_attributes": True}


class TicketComMensagensOut(TicketOut):
    mensagens: list[TicketMensagemOut] = []


class TicketAdminOut(TicketOut):
    """Para a lista do Super Admin — inclui de que escola veio (None = visitante anónimo)."""
    tenant_id: uuid.UUID | None
    nome_escola: str | None


class TicketAdminComMensagens(TicketAdminOut):
    """Para a conversa de UM ticket vista pelo Super Admin — mesmos
    campos da lista (TicketAdminOut) mais as mensagens. Sem isto, o
    detalhe do ticket não sabia de que escola era (nome_escola nunca
    chegava a existir no objeto ORM devolvido por obter_ticket_admin),
    e o frontend mostrava sempre "Visitante (sem conta)" mesmo para
    tickets de escolas reais."""
    mensagens: list[TicketMensagemOut] = []
