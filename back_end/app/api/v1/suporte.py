"""Suporte (tickets) da própria escola — ver app/api/v1/admin.py para o
equivalente cross-tenant do Super Admin, e app/api/v1/publico.py para o
formulário de contacto sem sessão e o chat de Suporte Virtual."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import suporte as crud_suporte
from app.schemas.suporte import MensagemTicketCreate, TicketCreate

router = APIRouter(prefix="/api/v1/suporte", tags=["Suporte"])

# Mesmo alcance operacional de /usuarios/auditoria e afins — Gestor e
# Secretaria, não Professor (que usa antes o Prof. Virtual dentro do
# Portal para dúvidas de matéria, não isto).
_PODE_ACEDER = exigir_perfil("GESTOR", "SECRETARIA")


@router.get("")
async def listar_meus_tickets(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_suporte.listar_meus_tickets(db, utilizador["tenant_id"], page, page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_ticket(
    dados: TicketCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Nome/e-mail vêm do próprio corpo do pedido (o frontend pré-preenche
    com os dados da conta, mas continua a ser um campo normal do
    formulário — mesma forma como o Contacto público funciona)."""
    ticket = await crud_suporte.criar_ticket_autenticado(
        db, utilizador["tenant_id"], dados.nome, dados.email, dados
    )
    return {"mensagem": "Pedido enviado à equipa de suporte.", "id": ticket.id}


@router.get("/{ticket_id}")
async def obter_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_suporte.obter_meu_ticket(db, ticket_id, utilizador["tenant_id"])


@router.post("/{ticket_id}/mensagens", status_code=status.HTTP_201_CREATED)
async def adicionar_mensagem(
    ticket_id: uuid.UUID, dados: MensagemTicketCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_ACEDER)
):
    await crud_suporte.adicionar_mensagem_cliente(db, ticket_id, utilizador["tenant_id"], utilizador["usuario_id"], dados)
    return {"mensagem": "Mensagem enviada."}
