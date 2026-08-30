import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db, obter_sessao_db_admin, obter_sessao_db_cross_tenant
from app.core.security import exigir_perfil
from app.cruds import transferencias as crud_transferencias
from app.schemas.transferencias import RejeitarTransferenciaRequest, SolicitacaoTransferenciaCreate

router = APIRouter(prefix="/api/v1/transferencias", tags=["Transferência de Alunos"])

_PODE_PEDIR = exigir_perfil("GESTOR", "SECRETARIA")
# Decisão é direta entre instituições — quem aprova/rejeita é o
# Gestor/Secretaria da escola de DESTINO (ver docstring de
# models_transferencias.py), não o Super Admin. _PODE_DECIDIR aqui só
# injeta utilizador/tenant_id na rota; o gate de facto (defesa em
# profundidade, mesmo padrão de obter_sessao_db_admin) está embutido
# na própria sessão — ver obter_sessao_db_cross_tenant.
_PODE_DECIDIR = exigir_perfil("GESTOR", "SECRETARIA")
_E_AUDITORIA_SUPER_ADMIN = exigir_perfil("SUPER_ADMIN")
_sessao_decisao_destino = obter_sessao_db_cross_tenant("GESTOR", "SECRETARIA")


@router.post("")
async def criar_solicitacao(
    dados: SolicitacaoTransferenciaCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_PEDIR)
):
    return await crud_transferencias.criar_solicitacao(db, utilizador["tenant_id"], utilizador, dados)


@router.get("/minhas")
async def listar_minhas_solicitacoes(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None), data_inicio: date | None = Query(None), data_fim: date | None = Query(None),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_PEDIR)
):
    return await crud_transferencias.listar_minhas_solicitacoes(
        db, utilizador["tenant_id"], page, page_size, status, data_inicio, data_fim
    )


@router.get("/recebidas")
async def listar_solicitacoes_recebidas(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    # Cross-tenant por natureza (lê Aluno/Tenant da escola de ORIGEM,
    # que pode ser qualquer escola da plataforma) — obter_sessao_db_cross_tenant
    # + filtro explícito por tenant_destino_id dentro do crud, mesmo
    # padrão do resto deste módulo.
    db: AsyncSession = Depends(_sessao_decisao_destino), utilizador: dict = Depends(_PODE_DECIDIR)
):
    return await crud_transferencias.listar_solicitacoes_recebidas(db, utilizador["tenant_id"], page, page_size)


@router.get("")
async def listar_solicitacoes_super_admin(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    # Cross-tenant por natureza (pedidos de QUALQUER escola de origem)
    # — obter_sessao_db (role app_tenant, com RLS) restringiria isto ao
    # tenant do próprio Super Admin e nunca encontraria nada de outras
    # escolas; obter_sessao_db_admin é o padrão já usado no resto do
    # Painel Super Admin para exactamente este caso (ver app/api/v1/admin.py).
    # Só auditoria/leitura — o Super Admin não decide (ver _PODE_DECIDIR acima).
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_E_AUDITORIA_SUPER_ADMIN)
):
    return await crud_transferencias.listar_solicitacoes_super_admin(db, page, page_size)


@router.patch("/{solicitacao_id}/aprovar")
async def aprovar_e_migrar(
    solicitacao_id: uuid.UUID,
    db: AsyncSession = Depends(_sessao_decisao_destino), utilizador: dict = Depends(_PODE_DECIDIR)
):
    return await crud_transferencias.aprovar_e_migrar(db, solicitacao_id, utilizador["tenant_id"])


@router.patch("/{solicitacao_id}/rejeitar")
async def rejeitar(
    solicitacao_id: uuid.UUID, dados: RejeitarTransferenciaRequest,
    db: AsyncSession = Depends(_sessao_decisao_destino), utilizador: dict = Depends(_PODE_DECIDIR)
):
    return await crud_transferencias.rejeitar(db, solicitacao_id, utilizador["tenant_id"], dados)
