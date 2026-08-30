"""Endpoints do site público (landing, preços, contacto, suporte
virtual) — sem autenticação. Mesmo prefixo /api/v1/public já usado pela
captação de Lead (ver app/api/v1/crm.py::router_publico), mas ficheiro
próprio por serem domínios diferentes (planos comerciais, tickets,
chat de IA — não CRM).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db_publica
from app.core.rate_limiter import excedeu_limite
from app.core.suporte_virtual import perguntar_suporte
from app.cruds import admin as crud_admin
from app.cruds import site_publico as crud_site_publico
from app.cruds import suporte as crud_suporte
from app.schemas.publico import PlanoSaaSPublicoOut
from app.schemas.site_publico import SitePublicoOut
from app.schemas.suporte import PerguntaSuporteVirtual, TicketCreate

router = APIRouter(prefix="/api/v1/public", tags=["Público"])


@router.get("/planos", response_model=list[PlanoSaaSPublicoOut])
async def listar_planos_publicos(db: AsyncSession = Depends(obter_sessao_db_publica)):
    """Planos ativos, para a página de Preços — resposta explicitamente
    tipada (response_model) para garantir que nenhum dado interno de
    gestão escapa por engano, ao contrário do endpoint equivalente do
    Super Admin que devolve os objetos ORM diretamente."""
    return await crud_admin.listar_planos_publicos(db)


def _resumo_planos_para_ia(planos: list) -> str:
    """Texto compacto dos planos ativos, injetado no prompt de sistema
    do Suporte Virtual (ver core/suporte_virtual.py) — é a ÚNICA fonte
    de preços que a IA pode citar, para nunca inventar valores."""
    if not planos:
        return "Ainda não há planos publicados — sugere ao visitante contactar a equipa através da página de Contacto."
    linhas = []
    for p in planos:
        modulos = ", ".join(f"{m.modulo} (+{m.preco_adicional})" for m in p.modulos if float(m.preco_adicional) > 0)
        extra = f"; módulos com custo adicional: {modulos}" if modulos else "; módulos essenciais incluídos, sem módulos extra com custo neste plano"
        teste = f"; {p.dias_periodo_teste} dias de período de teste" if p.dias_periodo_teste > 0 else ""
        linhas.append(f'- "{p.nome}": {p.preco_por_aluno} por aluno matriculado/mês{extra}{teste}.')
    return "\n".join(linhas)


# Custo real por mensagem (chamada à API da Anthropic) — limite por IP
# para impedir um script de esgotar o orçamento de IA da plataforma, o
# mesmo raciocínio do limitador de tentativas de login (ver
# api/v1/auth.py::_verificar_limite_login), só que aqui o "ataque" é ao
# bolso, não a uma conta.
_CHAT_MAX_MENSAGENS = 20
_CHAT_JANELA_SEGUNDOS = 600


@router.post("/suporte-virtual/perguntar")
async def perguntar_suporte_virtual(
    dados: PerguntaSuporteVirtual, request: Request,
    db: AsyncSession = Depends(obter_sessao_db_publica)
):
    ip_cliente = request.client.host if request.client else "desconhecido"
    if await excedeu_limite(f"suporte-virtual:{ip_cliente}", _CHAT_MAX_MENSAGENS, _CHAT_JANELA_SEGUNDOS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas mensagens seguidas — aguarde uns minutos ou contacte-nos pela página de Contacto."
        )
    planos = await crud_admin.listar_planos_publicos(db)
    resposta = await perguntar_suporte(dados.historico, dados.pergunta, _resumo_planos_para_ia(planos))
    return {"resposta": resposta}


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def criar_ticket_publico(dados: TicketCreate, db: AsyncSession = Depends(obter_sessao_db_publica)):
    """Formulário de Contacto do site público, sem sessão."""
    ticket = await crud_suporte.criar_ticket_publico(db, dados)
    return {"mensagem": "Recebemos o seu pedido — vamos responder por e-mail em breve.", "id": ticket.id}


@router.get("/escola/{tenant_id}", response_model=SitePublicoOut)
async def obter_site_publico(tenant_id: uuid.UUID, db: AsyncSession = Depends(obter_sessao_db_publica)):
    """Página de apresentação pública de UMA escola cliente (marketing/
    angariação de alunos) — 404 se a escola não existir ou não tiver
    ativado a página em Configurações (ver api/v1/configuracoes.py)."""
    return await crud_site_publico.obter_site_publico(db, tenant_id)
