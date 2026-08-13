from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.database.session import obter_sessao_db
from app.core.security import obter_utilizador_atual, exigir_perfil
from app.schemas.academico import CursoCreate, DisciplinaCreate, GradeCurricularCreate, SerieAnoCreate, TurmaCreate
from app.cruds import academico as crud_academico

# Quem pode criar/alterar a estrutura académica (RBAC) — leitura fica
# aberta a qualquer utilizador autenticado da escola.
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

router = APIRouter(prefix="/api/v1/academico", tags=["Módulo Académico"])

# ==========================================
# ROTAS PARA CURSOS
# ==========================================
@router.post("/cursos", status_code=status.HTTP_201_CREATED)
async def criar_curso(
    dados: CursoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria um novo curso associado à escola do utilizador logado."""
    return await crud_academico.criar_curso(db, utilizador["tenant_id"], dados)

@router.get("/cursos")
async def listar_cursos(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os cursos da escola do utilizador logado."""
    return await crud_academico.listar_cursos(db, utilizador["tenant_id"])

# ==========================================
# ROTAS PARA SÉRIES/ANOS
# ==========================================
# Camada intermédia entre Curso e Turma (ex: "10º Ano" dentro de
# "Ensino Secundário"). Uma Turma liga-se sempre a uma Série/Ano, nunca
# diretamente a um Curso.
@router.post("/series", status_code=status.HTTP_201_CREATED)
async def criar_serie_ano(
    dados: SerieAnoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria uma Série/Ano associada a um curso da escola do utilizador logado."""
    return await crud_academico.criar_serie_ano(db, utilizador["tenant_id"], dados)

@router.get("/series")
async def listar_series(
    curso_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista as Séries/Anos da escola do utilizador logado, opcionalmente filtradas por curso."""
    return await crud_academico.listar_series(db, utilizador["tenant_id"], curso_id)

# ==========================================
# ROTAS PARA TURMAS
# ==========================================
@router.post("/turmas", status_code=status.HTTP_201_CREATED)
async def criar_turma(
    dados: TurmaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria uma turma validando se a série/ano pertence à escola."""
    turma = await crud_academico.criar_turma(db, utilizador["tenant_id"], dados)
    return {"mensagem": "Turma criada com sucesso", "id": turma.id}

@router.get("/turmas")
async def listar_turmas(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista as turmas da escola do utilizador logado."""
    return await crud_academico.listar_turmas(db, utilizador["tenant_id"])

# ==========================================
# ROTAS PARA DISCIPLINAS
# ==========================================
@router.post("/disciplinas", status_code=status.HTTP_201_CREATED)
async def criar_disciplina(
    dados: DisciplinaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Cria uma nova disciplina (matéria) na escola do utilizador logado."""
    return await crud_academico.criar_disciplina(db, utilizador["tenant_id"], dados)

@router.get("/disciplinas")
async def listar_disciplinas(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista as disciplinas da escola do utilizador logado."""
    return await crud_academico.listar_disciplinas(db, utilizador["tenant_id"])

# ==========================================
# ROTAS PARA GRADE CURRICULAR (Série/Ano <-> Disciplina)
# ==========================================
@router.post("/grade-curricular", status_code=status.HTTP_201_CREATED)
async def adicionar_disciplina_a_serie(
    dados: GradeCurricularCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Associa uma disciplina a uma Série/Ano (define a grade curricular dessa série)."""
    item = await crud_academico.adicionar_disciplina_a_serie(db, utilizador["tenant_id"], dados)
    return {"mensagem": "Disciplina adicionada à grade curricular", "id": item.id}

@router.get("/grade-curricular")
async def listar_grade_curricular(
    serie_ano_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista a grade curricular da escola, opcionalmente filtrada por série/ano."""
    return await crud_academico.listar_grade_curricular(db, utilizador["tenant_id"], serie_ano_id)
