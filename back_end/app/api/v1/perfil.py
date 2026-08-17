"""
Área de Perfil — qualquer utilizador autenticado (GESTOR, SECRETARIA,
PROFESSOR, ALUNO, RESPONSAVEL, SUPER_ADMIN) vê/edita a própria conta.

Deliberadamente sem exigir_perfil: ao contrário de quase todos os
outros módulos, este não é restrito a nenhum subconjunto de perfis — só
exige um JWT válido (Depends(obter_utilizador_atual)), porque toda a
gente tem uma conta própria para gerir. Ver app/cruds/perfil.py.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import obter_utilizador_atual
from app.cruds import perfil as crud_perfil
from app.schemas.perfil import PerfilUpdate, AlterarSenhaIn

router = APIRouter(prefix="/api/v1/perfil", tags=["Perfil"])


@router.get("")
async def obter_perfil(
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_perfil.obter_perfil(db, utilizador["tenant_id"], utilizador["usuario_id"])


@router.put("")
async def atualizar_perfil(
    dados: PerfilUpdate,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_perfil.atualizar_perfil(db, utilizador["tenant_id"], utilizador["usuario_id"], dados)


@router.post("/alterar-senha")
async def alterar_senha(
    dados: AlterarSenhaIn,
    db: AsyncSession = Depends(obter_sessao_db), utilizador: dict = Depends(obter_utilizador_atual)
):
    await crud_perfil.alterar_senha(db, utilizador["tenant_id"], utilizador["usuario_id"], dados)
    return {"mensagem": "Palavra-passe alterada com sucesso."}
