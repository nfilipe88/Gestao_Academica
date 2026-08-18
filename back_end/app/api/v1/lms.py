from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil_staff
from app.schemas.lms import (
    LMSExameCreate, LMSQuestaoCreate, LMSQuestaoUpdate,
    MaterialAulaCreate, MaterialAulaUpdate, SugestaoConteudoCreate
)
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


# ==========================================
# BANCO DE QUESTÕES
# ==========================================
@router.get("/disciplinas/{disciplina_id}/questoes")
async def listar_banco_questoes(
    disciplina_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Banco de questões de uma disciplina — reutilizável em vários exames."""
    return await crud_lms.listar_banco_questoes(db, utilizador, disciplina_id)


@router.post("/questoes", status_code=status.HTTP_201_CREATED)
async def criar_questao(
    dados: LMSQuestaoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Cria uma questão (escolha múltipla ou verdadeiro/falso) no banco de questões."""
    return await crud_lms.criar_questao(db, utilizador, dados)


@router.patch("/questoes/{questao_id}")
async def atualizar_questao(
    questao_id: uuid.UUID,
    dados: LMSQuestaoUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Edita uma questão do banco."""
    return await crud_lms.atualizar_questao(db, utilizador, questao_id, dados)


@router.delete("/questoes/{questao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_questao(
    questao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Apaga uma questão — recusa se já foi usada nalgum exame."""
    await crud_lms.apagar_questao(db, utilizador, questao_id)


# ==========================================
# EXAMES (motor online)
# ==========================================
@router.get("/alocacoes/{alocacao_id}/exames")
async def listar_exames(
    alocacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Exames desta alocação (turma+disciplina de um professor)."""
    return await crud_lms.listar_exames(db, utilizador, alocacao_id)


@router.post("/exames", status_code=status.HTTP_201_CREATED)
async def criar_exame(
    dados: LMSExameCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Cria um exame (rascunho — usar PATCH .../publicar para o abrir aos alunos), com a lista de questões já associada."""
    return await crud_lms.criar_exame(db, utilizador, dados)


@router.get("/exames/{exame_id}")
async def obter_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Detalhe do exame com o gabarito de cada questão."""
    return await crud_lms.obter_exame_com_gabarito(db, utilizador, exame_id)


@router.patch("/exames/{exame_id}/publicar")
async def publicar_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Publica o exame — a partir daqui os alunos da turma podem vê-lo e iniciar tentativas dentro da janela definida."""
    return await crud_lms.alternar_publicacao_exame(db, utilizador, exame_id, True)


@router.patch("/exames/{exame_id}/despublicar")
async def despublicar_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Volta o exame a rascunho — tentativas já em curso/submetidas não são apagadas."""
    return await crud_lms.alternar_publicacao_exame(db, utilizador, exame_id, False)


@router.delete("/exames/{exame_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Apaga o exame — recusa se já houver tentativas de alunos."""
    await crud_lms.apagar_exame(db, utilizador, exame_id)


@router.get("/exames/{exame_id}/resultados")
async def listar_resultados_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Notas de quem já começou/submeteu este exame."""
    return await crud_lms.listar_resultados_exame(db, utilizador, exame_id)
