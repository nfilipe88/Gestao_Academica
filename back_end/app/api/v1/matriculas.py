from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel
import uuid

from app.database.session import obter_sessao_db
from app.database.models_academico import Turma
from app.database.models_pessoas import Aluno
from app.database.models_matricula import Matricula
from app.core.security import obter_utilizador_atual, exigir_perfil

router = APIRouter(prefix="/api/v1", tags=["Matrículas"])

# Quem pode matricular/alterar status (RBAC) — leitura fica aberta a
# qualquer utilizador autenticado da escola.
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

ESTADOS_VALIDOS = {"ATIVO", "TRANSFERIDO", "TRANCADO", "EVADIDO"}

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class MatriculaCreate(BaseModel):
    aluno_id: uuid.UUID
    turma_id: uuid.UUID
    ano_letivo: int

class MatriculaStatusUpdate(BaseModel):
    status_matricula: str
    motivo: str | None = None

# ==========================================
# A. CRIAR NOVA MATRÍCULA
# ==========================================
@router.post("/matriculas", status_code=status.HTTP_201_CREATED)
async def criar_matricula(
    dados: MatriculaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Efetua a matrícula de um aluno numa turma, aplicando as regras de negócio RN01-RN05."""
    tenant_id = utilizador["tenant_id"]

    # RN01 + RN05 - Isolamento de tenant e integridade: aluno e turma têm
    # de existir e pertencer à mesma escola do utilizador.
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == dados.aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    turma = (await db.execute(
        select(Turma).where(Turma.id == dados.turma_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    # RN03 - Prevenção de Duplicidade
    duplicado = (await db.execute(
        select(Matricula).where(
            Matricula.aluno_id == dados.aluno_id,
            Matricula.turma_id == dados.turma_id,
            Matricula.ano_letivo == dados.ano_letivo
        )
    )).scalars().first()
    if duplicado:
        raise HTTPException(status_code=400, detail="Este aluno já está matriculado nesta turma neste ano letivo.")

    # RN02 - Controlo de Vagas (só conta matrículas ATIVAS)
    total_ativas = (await db.execute(
        select(func.count()).select_from(Matricula).where(
            Matricula.turma_id == dados.turma_id,
            Matricula.status_matricula == "ATIVO"
        )
    )).scalar_one()
    if total_ativas >= turma.vagas_maximas:
        raise HTTPException(status_code=400, detail="Turma lotada — não há vagas disponíveis.")

    # RN04 - Status Inicial "ATIVO"
    nova_matricula = Matricula(
        tenant_id=tenant_id,
        aluno_id=dados.aluno_id,
        turma_id=dados.turma_id,
        ano_letivo=dados.ano_letivo,
        status_matricula="ATIVO"
    )
    db.add(nova_matricula)
    await db.commit()
    await db.refresh(nova_matricula)
    return nova_matricula

# ==========================================
# B. LISTAR MATRÍCULAS DE UMA TURMA (Diário de Classe)
# ==========================================
@router.get("/turmas/{turma_id}/matriculas")
async def listar_matriculas_da_turma(
    turma_id: uuid.UUID,
    status_matricula: str | None = None,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os alunos matriculados numa turma. ?status_matricula=ATIVO filtra só os ativos."""
    query = (
        select(Matricula, Aluno.nome_completo, Aluno.matricula_interna)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(Matricula.turma_id == turma_id, Matricula.tenant_id == utilizador["tenant_id"])
    )
    if status_matricula:
        query = query.where(Matricula.status_matricula == status_matricula)

    resultado = await db.execute(query)
    return [
        {
            "matricula_id": matricula.id,
            "aluno_id": matricula.aluno_id,
            "nome_aluno": nome_aluno,
            "matricula_interna": matricula_interna,
            "status_matricula": matricula.status_matricula,
            "ano_letivo": matricula.ano_letivo,
            "data_matricula": matricula.data_matricula,
        }
        for matricula, nome_aluno, matricula_interna in resultado.all()
    ]

# ==========================================
# C. ALTERAR STATUS DA MATRÍCULA
# ==========================================
@router.patch("/matriculas/{matricula_id}/status")
async def atualizar_status_matricula(
    matricula_id: uuid.UUID,
    dados: MatriculaStatusUpdate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Atualiza a situação do aluno (ex: de Ativo para Trancado, Transferido ou Evadido)."""
    if dados.status_matricula not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Use um de: {', '.join(sorted(ESTADOS_VALIDOS))}."
        )

    matricula = (await db.execute(
        select(Matricula).where(Matricula.id == matricula_id, Matricula.tenant_id == utilizador["tenant_id"])
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada na sua instituição.")

    matricula.status_matricula = dados.status_matricula
    await db.commit()
    return {"mensagem": "Status da matrícula atualizado com sucesso."}

# ==========================================
# D. CONSULTAR HISTÓRICO DO ALUNO
# ==========================================
@router.get("/alunos/{aluno_id}/matriculas")
async def listar_matriculas_do_aluno(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Mostra todas as turmas e anos letivos pelos quais o aluno já passou na escola."""
    resultado = await db.execute(
        select(Matricula, Turma.nome_codigo).join(Turma, Turma.id == Matricula.turma_id).where(
            Matricula.aluno_id == aluno_id, Matricula.tenant_id == utilizador["tenant_id"]
        )
    )
    return [
        {
            "matricula_id": matricula.id,
            "turma_id": matricula.turma_id,
            "nome_turma": nome_turma,
            "status_matricula": matricula.status_matricula,
            "ano_letivo": matricula.ano_letivo,
            "data_matricula": matricula.data_matricula,
        }
        for matricula, nome_turma in resultado.all()
    ]
