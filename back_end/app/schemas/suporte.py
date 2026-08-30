"""Schemas do Suporte Virtual (chat de IA) e do sistema de tickets — ver
app/core/suporte_virtual.py e app/cruds/suporte.py."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
import uuid

# ==========================================
# Suporte Virtual (chat de IA, sem BD)
# ==========================================

class MensagemChatSuporte(BaseModel):
    papel: str  # "visitante" | "assistente"
    texto: str


class PerguntaSuporteVirtual(BaseModel):
    historico: list[MensagemChatSuporte] = []
    pergunta: str = Field(..., min_length=1, max_length=1000)


# ==========================================
# Tickets
# ==========================================

class TicketCreate(BaseModel):
    """Usado tanto pelo formulário público (/contacto, sem sessão) como
    pelo staff já autenticado — a rota autenticada ignora nome/email
    daqui e usa os do próprio utilizador (ver api/v1/suporte.py)."""
    nome: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    assunto: str = Field(..., min_length=1, max_length=200)
    mensagem: str = Field(..., min_length=1, max_length=5000)


class MensagemTicketCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=5000)


class TicketEstadoUpdate(BaseModel):
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
