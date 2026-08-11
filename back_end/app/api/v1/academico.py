from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid

from app.database.session import obter_sessao_db
from app.database.models_academico import Curso, Disciplina, GradeCurricular, SerieAno, Turma
from app.core.security import obter_utilizador_atual, exigir_perfil

# Quem pode criar/alterar a estrutura académica (RBAC) — leitura fica
# aberta a qualquer utilizador autenticado da escola.
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

router = APIRouter(prefix="/api/v1/academico", tags=["Módulo Académico"])

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class CursoCreate(BaseModel):
    nome: str

class SerieAnoCreate(BaseModel):
    curso_id: uuid.UUID
    nome: str

class TurmaCreate(BaseModel):
    serie_ano_id: uuid.UUID
    nome_codigo: str
    ano_letivo: int
    vagas_maximas: int = 30

class DisciplinaCreate(BaseModel):
    nome: str
    carga_horaria_total: Optional[int] = None

class GradeCurricularCreate(BaseModel):
    serie_ano_id: uuid.UUID
    disciplina_id: uuid.UUID

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
    novo_curso = Curso(
        nome=dados.nome,
        tenant_id=utilizador["tenant_id"] # Injetamos o tenant de forma segura
    )
    db.add(novo_curso)
    await db.commit()
    await db.refresh(novo_curso)
    return novo_curso

@router.get("/cursos")
async def listar_cursos(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """
    Lista os cursos da escola do utilizador logado.
    O RLS do Postgres é a última linha de defesa, mas filtramos também
    explicitamente por tenant_id para não depender só dele.
    """
    resultado = await db.execute(
        select(Curso).where(Curso.tenant_id == utilizador["tenant_id"])
    )
    cursos = resultado.scalars().all()
    return cursos

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
    curso_db = await db.execute(
        select(Curso).where(
            Curso.id == dados.curso_id,
            Curso.tenant_id == utilizador["tenant_id"]
        )
    )
    if not curso_db.scalars().first():
        raise HTTPException(status_code=404, detail="Curso não encontrado na sua instituição.")

    nova_serie = SerieAno(
        curso_id=dados.curso_id,
        nome=dados.nome,
        tenant_id=utilizador["tenant_id"]
    )
    db.add(nova_serie)
    await db.commit()
    await db.refresh(nova_serie)
    return nova_serie

@router.get("/series")
async def listar_series(
    curso_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista as Séries/Anos da escola do utilizador logado, opcionalmente filtradas por curso."""
    query = select(SerieAno).where(SerieAno.tenant_id == utilizador["tenant_id"])
    if curso_id:
        query = query.where(SerieAno.curso_id == curso_id)
    resultado = await db.execute(query)
    series = resultado.scalars().all()
    return series

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

    # 1. Validar se a série/ano existe E pertence à mesma escola do utilizador
    # (filtro explícito, não só o RLS — mesma lógica aplicada em listar_cursos/listar_turmas).
    serie_db = await db.execute(
        select(SerieAno).where(
            SerieAno.id == dados.serie_ano_id,
            SerieAno.tenant_id == utilizador["tenant_id"]
        )
    )
    if not serie_db.scalars().first():
        raise HTTPException(status_code=404, detail="Série/Ano não encontrada na sua instituição.")

    # 2. Criar a Turma
    nova_turma = Turma(
        tenant_id=utilizador["tenant_id"],
        serie_ano_id=dados.serie_ano_id,
        nome_codigo=dados.nome_codigo,
        ano_letivo=dados.ano_letivo,
        vagas_maximas=dados.vagas_maximas
    )
    db.add(nova_turma)
    await db.commit()
    return {"mensagem": "Turma criada com sucesso", "id": nova_turma.id}

@router.get("/turmas")
async def listar_turmas(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """
    Lista as turmas da escola do utilizador logado (filtro explícito por
    tenant_id, com o RLS do Postgres como camada extra de defesa).
    """
    resultado = await db.execute(
        select(Turma).where(Turma.tenant_id == utilizador["tenant_id"])
    )
    turmas = resultado.scalars().all()
    return turmas

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
    nova_disciplina = Disciplina(
        tenant_id=utilizador["tenant_id"],
        nome=dados.nome,
        carga_horaria_total=dados.carga_horaria_total
    )
    db.add(nova_disciplina)
    await db.commit()
    await db.refresh(nova_disciplina)
    return nova_disciplina

@router.get("/disciplinas")
async def listar_disciplinas(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista as disciplinas da escola do utilizador logado."""
    resultado = await db.execute(
        select(Disciplina).where(Disciplina.tenant_id == utilizador["tenant_id"])
    )
    return resultado.scalars().all()

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
    tenant_id = utilizador["tenant_id"]

    serie = (await db.execute(
        select(SerieAno).where(SerieAno.id == dados.serie_ano_id, SerieAno.tenant_id == tenant_id)
    )).scalars().first()
    if not serie:
        raise HTTPException(status_code=404, detail="Série/Ano não encontrada na sua instituição.")

    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == dados.disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")

    ja_existe = (await db.execute(
        select(GradeCurricular).where(
            GradeCurricular.serie_ano_id == dados.serie_ano_id,
            GradeCurricular.disciplina_id == dados.disciplina_id
        )
    )).scalars().first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Esta disciplina já está associada a esta série/ano.")

    novo_item = GradeCurricular(
        tenant_id=tenant_id,
        serie_ano_id=dados.serie_ano_id,
        disciplina_id=dados.disciplina_id
    )
    db.add(novo_item)
    await db.commit()
    return {"mensagem": "Disciplina adicionada à grade curricular", "id": novo_item.id}

@router.get("/grade-curricular")
async def listar_grade_curricular(
    serie_ano_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista a grade curricular da escola, opcionalmente filtrada por série/ano."""
    query = select(GradeCurricular).where(GradeCurricular.tenant_id == utilizador["tenant_id"])
    if serie_ano_id:
        query = query.where(GradeCurricular.serie_ano_id == serie_ano_id)
    resultado = await db.execute(query)
    return resultado.scalars().all()
