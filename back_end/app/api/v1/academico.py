from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.database.session import obter_sessao_db
from app.database.models_academico import Curso, Turma
from app.core.security import obter_utilizador_atual

router = APIRouter(prefix="/api/v1/academico", tags=["Módulo Académico"])

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class CursoCreate(BaseModel):
    nome: str

class TurmaCreate(BaseModel):
    curso_id: uuid.UUID
    nome_codigo: str
    ano_letivo: int
    vagas_maximas: int = 30

# ==========================================
# ROTAS PARA CURSOS
# ==========================================
@router.post("/cursos", status_code=status.HTTP_201_CREATED)
async def criar_curso(
    dados: CursoCreate, 
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
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
# ROTAS PARA TURMAS
# ==========================================
@router.post("/turmas", status_code=status.HTTP_201_CREATED)
async def criar_turma(
    dados: TurmaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Cria uma turma validando se o curso pertence à escola."""
    
    # 1. Validar se o curso existe (o RLS já impede que ele encontre um curso de outra escola)
    curso_db = await db.execute(select(Curso).where(Curso.id == dados.curso_id))
    if not curso_db.scalars().first():
        raise HTTPException(status_code=404, detail="Curso não encontrado na sua instituição.")

    # 2. Criar a Turma
    nova_turma = Turma(
        tenant_id=utilizador["tenant_id"],
        curso_id=dados.curso_id,
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