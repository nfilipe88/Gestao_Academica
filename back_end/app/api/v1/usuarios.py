"""Gestão de Acessos — Gestor gere o staff da própria escola.

Ver app/api/v1/admin.py para o equivalente do Super Admin (qualquer
escola) — ambos chamam as mesmas funções em app/cruds/usuarios.py.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import usuarios as crud_usuarios
from app.schemas.usuarios import AtivoUpdate, PerfilAcessoUpdate, SecretariaCreate

router = APIRouter(prefix="/api/v1/usuarios", tags=["Gestão de Acessos"])

# Gestão de perfis/suspensão fica só ao critério do Gestor — a
# Secretaria já tem bastante poder administrativo noutros módulos, mas
# decidir QUEM tem esse poder é uma decisão de topo da escola.
_PODE_GERIR = exigir_perfil("GESTOR")


@router.get("")
async def listar_usuarios(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)
):
    """Staff da própria escola (Gestor/Secretaria/Professor)."""
    return await crud_usuarios.listar_usuarios(db, utilizador["tenant_id"], page, page_size)


@router.post("/secretaria", status_code=status.HTTP_201_CREATED)
async def criar_secretaria(
    dados: SecretariaCreate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria uma conta de Secretaria na própria escola."""
    novo = await crud_usuarios.criar_secretaria(db, utilizador["tenant_id"], dados, utilizador["usuario_id"])
    return {"mensagem": f'Conta de Secretaria criada para "{novo.nome_completo}".', "id": novo.id}


@router.patch("/{usuario_id}/perfil")
async def alterar_perfil(
    usuario_id: uuid.UUID, dados: PerfilAcessoUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)
):
    """Muda o perfil entre Gestor e Secretaria (não se aplica a Professor/Aluno/Responsável — ver docstring do crud)."""
    alterado = await crud_usuarios.alterar_perfil(db, utilizador["tenant_id"], usuario_id, dados, utilizador["usuario_id"])
    return {"mensagem": f'"{alterado.nome_completo}" passou a ter o perfil {alterado.perfil_acesso}.', "perfil_acesso": alterado.perfil_acesso}


@router.patch("/{usuario_id}/ativo")
async def alterar_estado_ativo(
    usuario_id: uuid.UUID, dados: AtivoUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)
):
    """Suspende ou reativa o acesso de UM utilizador (não afeta o resto da escola)."""
    alterado = await crud_usuarios.alterar_estado_ativo(db, utilizador["tenant_id"], usuario_id, dados.ativo, utilizador["usuario_id"])
    return {"mensagem": f'"{alterado.nome_completo}" agora está {"ativo" if alterado.ativo else "suspenso"}.', "ativo": alterado.ativo}


@router.get("/auditoria")
async def listar_auditoria(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(_PODE_GERIR)
):
    """Histórico de criação de contas, mudanças de perfil e suspensões/reativações da própria escola."""
    return await crud_usuarios.listar_auditoria(db, utilizador["tenant_id"], page, page_size)
