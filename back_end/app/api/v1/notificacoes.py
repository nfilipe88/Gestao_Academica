import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import obter_utilizador_atual
from app.cruds import notificacoes as crud_notificacoes

router = APIRouter(prefix="/api/v1/notificacoes", tags=["Notificações"])

# Qualquer perfil autenticado tem as suas próprias notificações — não há
# restrição de RBAC aqui, só o filtro implícito por usuario_id/tenant_id.


@router.get("")
async def listar_minhas_notificacoes(
    apenas_nao_lidas: bool = False,
    limite: int = 50,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """As minhas notificações, mais recentes primeiro."""
    return await crud_notificacoes.listar_minhas_notificacoes(
        db, utilizador["tenant_id"], utilizador["usuario_id"], apenas_nao_lidas, limite
    )


@router.get("/contagem")
async def contar_nao_lidas(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Número de notificações por ler — usado para o distintivo (badge) no sino da barra superior."""
    total = await crud_notificacoes.contar_nao_lidas(db, utilizador["tenant_id"], utilizador["usuario_id"])
    return {"total_nao_lidas": total}


@router.patch("/{notificacao_id}/marcar-lida")
async def marcar_como_lida(
    notificacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_notificacoes.marcar_como_lida(
        db, utilizador["tenant_id"], utilizador["usuario_id"], notificacao_id
    )


@router.patch("/marcar-todas-lidas")
async def marcar_todas_como_lidas(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    total = await crud_notificacoes.marcar_todas_como_lidas(db, utilizador["tenant_id"], utilizador["usuario_id"])
    return {"total_marcadas": total}
