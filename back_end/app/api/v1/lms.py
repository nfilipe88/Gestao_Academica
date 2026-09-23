from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.schemas.lms import (
    LMSCorrigirTentativaInput, LMSGrupoExameCreate, LMSQuestaoCreate, LMSQuestaoUpdate, LMSReatribuirVarianteInput,
    MaterialAulaCreate, MaterialAulaUpdate, SugestaoConteudoCreate
)
from app.cruds import lms as crud_lms

router = APIRouter(prefix="/api/v1/lms", tags=["LMS — Materiais de Aula"])

# Gatilho exclusivo de Gestor/Secretaria, distinto de exigir_perfil_staff
# (que também deixa o Professor preparar/publicar) — mesmo padrão de
# _PODE_GERIR_PERIODOS em api/v1/diario.py. Só a partir daqui os alunos
# conseguem mesmo começar (ver cruds/lms.py::_obter_exame_publicado_da_turma).
_PODE_INICIAR_EXAME = exigir_perfil("GESTOR", "SECRETARIA")


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
# EXAMES (motor online) — um GRUPO de 1+ variantes, ligado a uma
# Avaliacao do Diário (ver schemas/lms.py::LMSGrupoExameCreate)
# ==========================================
@router.get("/alocacoes/{alocacao_id}/grupos-exame")
async def listar_grupos_exame(
    alocacao_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Grupos de exame (cada um com 1+ variantes) desta alocação (turma+disciplina de um professor)."""
    return await crud_lms.listar_grupos_exame(db, utilizador, alocacao_id)


@router.post("/grupos-exame", status_code=status.HTTP_201_CREATED)
async def criar_grupo_exame(
    dados: LMSGrupoExameCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Cria um grupo de exame (rascunho — usar PATCH .../iniciar para o abrir aos alunos), com 1+ variantes e a Avaliacao do Diário que vai receber as notas."""
    return await crud_lms.criar_grupo_exame(db, utilizador, dados)


@router.patch("/grupos-exame/{grupo_id}/iniciar")
async def iniciar_grupo_exame(
    grupo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_INICIAR_EXAME)
):
    """Só Gestor/Secretaria — abre o grupo aos alunos e distribui cada aluno por round-robin entre as variantes."""
    return await crud_lms.iniciar_grupo_exame(db, utilizador, grupo_id)


@router.patch("/grupos-exame/{grupo_id}/reatribuir")
async def reatribuir_variante_aluno(
    grupo_id: uuid.UUID,
    dados: LMSReatribuirVarianteInput,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_INICIAR_EXAME)
):
    """Só Gestor/Secretaria — reatribui manualmente um aluno a outra variante do mesmo grupo (bloqueado se já tiver tentativa em curso)."""
    return await crud_lms.reatribuir_variante_aluno(db, utilizador, grupo_id, dados)


@router.get("/grupos-exame/{grupo_id}/atribuicoes")
async def listar_atribuicoes_grupo(
    grupo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Quem está atribuído a cada variante — alimenta a tabela de reatribuição manual. Vazio antes do INICIAR."""
    return await crud_lms.listar_atribuicoes_grupo(db, utilizador, grupo_id)


@router.delete("/grupos-exame/{grupo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_grupo_exame(
    grupo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Apaga todas as variantes do grupo — recusa se já houver tentativas de alunos."""
    await crud_lms.apagar_grupo_exame(db, utilizador, grupo_id)


@router.get("/grupos-exame/{grupo_id}/resultados")
async def listar_resultados_grupo(
    grupo_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Resultados agregados de todas as variantes do grupo, com a letra da variante em cada linha."""
    return await crud_lms.listar_resultados_grupo(db, utilizador, grupo_id)


@router.get("/exames/{exame_id}")
async def obter_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Detalhe de uma variante com o gabarito de cada questão."""
    return await crud_lms.obter_exame_com_gabarito(db, utilizador, exame_id)


@router.patch("/exames/{exame_id}/publicar")
async def publicar_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Publica esta variante — sozinho não chega para os alunos começarem, é preciso também PATCH .../grupos-exame/{grupo_id}/iniciar (ver docstring de LMSExame)."""
    return await crud_lms.alternar_publicacao_exame(db, utilizador, exame_id, True)


@router.patch("/exames/{exame_id}/despublicar")
async def despublicar_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Esconde temporariamente esta variante — tentativas já em curso/submetidas não são apagadas."""
    return await crud_lms.alternar_publicacao_exame(db, utilizador, exame_id, False)


@router.get("/exames/{exame_id}/resultados")
async def listar_resultados_exame(
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Notas de quem já começou/submeteu esta variante."""
    return await crud_lms.listar_resultados_exame(db, utilizador, exame_id)


@router.post("/exames/{exame_id}/tentativas/{matricula_id}/corrigir")
async def corrigir_tentativa(
    exame_id: uuid.UUID,
    matricula_id: uuid.UUID,
    dados: LMSCorrigirTentativaInput,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Corrige questões de resposta aberta pendentes e/ou sobrescreve/
    finaliza diretamente o total de uma tentativa — cobre também o caso
    de uma prova presencial já 100% corrigida automaticamente, onde o
    professor quer validar/lançar a nota final na mesma."""
    return await crud_lms.corrigir_tentativa(db, utilizador, exame_id, matricula_id, dados)
