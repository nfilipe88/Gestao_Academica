"""
Acesso a dados de Notificações in-app.

criar_notificacao/criar_notificacoes_em_lote são chamadas diretamente
por outros cruds (Comunicações, Solicitações de Documentos,
Transferências, avisos de licença) na mesma sessão/transação — não há
aqui nenhuma verificação de permissão própria, porque quem chama já
decidiu (com as suas próprias regras) quem deve ser notificado.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_notificacoes import Notificacao


# ==========================================
# CRIAÇÃO (usada por outros módulos)
# ==========================================
async def criar_notificacao(
    db: AsyncSession, tenant_id, usuario_id: uuid.UUID, tipo: str, titulo: str, mensagem: str, link: str | None = None
) -> Notificacao:
    nova = Notificacao(
        tenant_id=tenant_id, usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensagem=mensagem, link=link
    )
    db.add(nova)
    await db.commit()
    return nova


async def criar_notificacoes_em_lote(
    db: AsyncSession, tenant_id, usuario_ids: list[uuid.UUID], tipo: str, titulo: str, mensagem: str, link: str | None = None
) -> int:
    """Mesmo alerta para vários utilizadores de uma vez (ex: todos os destinatários de um Comunicado)."""
    if not usuario_ids:
        return 0
    for usuario_id in set(usuario_ids):
        db.add(Notificacao(
            tenant_id=tenant_id, usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensagem=mensagem, link=link
        ))
    await db.commit()
    return len(set(usuario_ids))


# ==========================================
# LEITURA (do próprio utilizador autenticado)
# ==========================================
def _serializar(notificacao: Notificacao) -> dict:
    return {
        "id": notificacao.id,
        "tipo": notificacao.tipo,
        "titulo": notificacao.titulo,
        "mensagem": notificacao.mensagem,
        "link": notificacao.link,
        "lida": notificacao.lida,
        "data_criacao": notificacao.data_criacao,
    }


async def listar_minhas_notificacoes(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, apenas_nao_lidas: bool = False, limite: int = 50) -> list[dict]:
    query = select(Notificacao).where(Notificacao.tenant_id == tenant_id, Notificacao.usuario_id == usuario_id)
    if apenas_nao_lidas:
        query = query.where(Notificacao.lida.is_(False))
    query = query.order_by(Notificacao.data_criacao.desc()).limit(limite)

    notificacoes = (await db.execute(query)).scalars().all()
    return [_serializar(n) for n in notificacoes]


async def contar_nao_lidas(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> int:
    return (await db.execute(
        select(func.count(Notificacao.id)).where(
            Notificacao.tenant_id == tenant_id, Notificacao.usuario_id == usuario_id, Notificacao.lida.is_(False)
        )
    )).scalar_one()


async def marcar_como_lida(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, notificacao_id: uuid.UUID) -> Notificacao:
    notificacao = (await db.execute(
        select(Notificacao).where(
            Notificacao.id == notificacao_id, Notificacao.tenant_id == tenant_id, Notificacao.usuario_id == usuario_id
        )
    )).scalars().first()
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.data_leitura = datetime.now(timezone.utc)
        await db.commit()
    return notificacao


async def marcar_todas_como_lidas(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> int:
    nao_lidas = (await db.execute(
        select(Notificacao).where(
            Notificacao.tenant_id == tenant_id, Notificacao.usuario_id == usuario_id, Notificacao.lida.is_(False)
        )
    )).scalars().all()
    agora = datetime.now(timezone.utc)
    for notificacao in nao_lidas:
        notificacao.lida = True
        notificacao.data_leitura = agora
    await db.commit()
    return len(nao_lidas)
