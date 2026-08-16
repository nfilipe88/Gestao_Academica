from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil_staff
from app.schemas.lms import MaterialAulaCreate, MaterialAulaUpdate, SugestaoConteudoCreate
from app.cruds import lms as crud_lms

router = APIRouter(prefix="/api/v1/lms", tags=["LMS — Materiais de Aula"])


@router.get("/turmas/{turma_id}/disciplinas/{disciplina_id}/materiais")
async def listar_materiais(
    turma_id: uuid.UUID,
    disciplina_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista os materiais de aula de uma turma+disciplina — o Professor precisa de estar alocado (validado no crud)."""
    return await crud_lms.listar_materiais(db, utilizador, turma_id, disciplina_id)


@router.post("/materiais", status_code=status.HTTP_201_CREATED)
async def criar_material(
    dados: MaterialAulaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Publica um novo material de aula."""
    return await crud_lms.criar_material(db, utilizador, dados)


@router.patch("/materiais/{material_id}")
async def atualizar_material(
    material_id: uuid.UUID,
    dados: MaterialAulaUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Edita título/corpo/objetivo/estado de publicação de um material."""
    return await crud_lms.atualizar_material(db, utilizador, material_id, dados)


@router.delete("/materiais/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_material(
    material_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Apaga um material de aula."""
    await crud_lms.apagar_material(db, utilizador, material_id)


@router.post("/materiais/sugestao-conteudo")
async def sugerir_conteudo(
    dados: SugestaoConteudoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Pede ao Prof. Virtual um rascunho do campo Conteúdo, a partir do título — o professor revê antes de publicar."""
    sugestao = await crud_lms.sugerir_conteudo(db, utilizador, dados)
    return {"sugestao": sugestao}
