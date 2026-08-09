from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date
import uuid

from app.database.session import obter_sessao_db
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.core.security import obter_utilizador_atual

router = APIRouter(prefix="/api/v1", tags=["Alunos e Responsáveis"])

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class AlunoCreate(BaseModel):
    matricula_interna: str
    nome_completo: str
    data_nascimento: date
    numero_documento: str | None = None

class ResponsavelCreate(BaseModel):
    nome_completo: str
    telefone_contato: str
    numero_documento: str | None = None

class VincularResponsavel(BaseModel):
    responsavel_id: uuid.UUID
    tipo_parentesco: str
    responsavel_financeiro: bool = False

# ==========================================
# ROTAS PARA ALUNOS
# ==========================================
@router.post("/alunos", status_code=status.HTTP_201_CREATED)
async def criar_aluno(
    dados: AlunoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Cria um novo aluno na escola do utilizador logado."""
    ja_existe = await db.execute(
        select(Aluno).where(
            Aluno.tenant_id == utilizador["tenant_id"],
            Aluno.matricula_interna == dados.matricula_interna
        )
    )
    if ja_existe.scalars().first():
        raise HTTPException(status_code=400, detail="Já existe um aluno com esta matrícula interna.")

    novo_aluno = Aluno(
        tenant_id=utilizador["tenant_id"],
        matricula_interna=dados.matricula_interna,
        nome_completo=dados.nome_completo,
        data_nascimento=dados.data_nascimento,
        numero_documento=dados.numero_documento
    )
    db.add(novo_aluno)
    await db.commit()
    await db.refresh(novo_aluno)
    return novo_aluno

@router.get("/alunos")
async def listar_alunos(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os alunos da escola do utilizador logado."""
    resultado = await db.execute(
        select(Aluno).where(Aluno.tenant_id == utilizador["tenant_id"])
    )
    return resultado.scalars().all()

# ==========================================
# ROTAS PARA RESPONSÁVEIS
# ==========================================
@router.post("/responsaveis", status_code=status.HTTP_201_CREATED)
async def criar_responsavel(
    dados: ResponsavelCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Cria um novo responsável (Pai/Mãe/Tutor) na escola do utilizador logado."""
    novo_responsavel = ResponsavelFinanceiroLegal(
        tenant_id=utilizador["tenant_id"],
        nome_completo=dados.nome_completo,
        telefone_contato=dados.telefone_contato,
        numero_documento=dados.numero_documento
    )
    db.add(novo_responsavel)
    await db.commit()
    await db.refresh(novo_responsavel)
    return novo_responsavel

@router.get("/responsaveis")
async def listar_responsaveis(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os responsáveis da escola do utilizador logado."""
    resultado = await db.execute(
        select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.tenant_id == utilizador["tenant_id"])
    )
    return resultado.scalars().all()

# ==========================================
# VÍNCULO ALUNO <-> RESPONSÁVEL
# ==========================================
@router.post("/alunos/{aluno_id}/responsaveis", status_code=status.HTTP_201_CREATED)
async def vincular_responsavel(
    aluno_id: uuid.UUID,
    dados: VincularResponsavel,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Vincula um responsável já existente a um aluno (RN: um aluno pode ter vários responsáveis)."""
    aluno_db = await db.execute(
        select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == utilizador["tenant_id"])
    )
    if not aluno_db.scalars().first():
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    responsavel_db = await db.execute(
        select(ResponsavelFinanceiroLegal).where(
            ResponsavelFinanceiroLegal.id == dados.responsavel_id,
            ResponsavelFinanceiroLegal.tenant_id == utilizador["tenant_id"]
        )
    )
    if not responsavel_db.scalars().first():
        raise HTTPException(status_code=404, detail="Responsável não encontrado na sua instituição.")

    ja_vinculado = await db.execute(
        select(AlunoResponsavel).where(
            AlunoResponsavel.aluno_id == aluno_id,
            AlunoResponsavel.responsavel_id == dados.responsavel_id
        )
    )
    if ja_vinculado.scalars().first():
        raise HTTPException(status_code=400, detail="Este responsável já está vinculado a este aluno.")

    vinculo = AlunoResponsavel(
        tenant_id=utilizador["tenant_id"],
        aluno_id=aluno_id,
        responsavel_id=dados.responsavel_id,
        tipo_parentesco=dados.tipo_parentesco,
        responsavel_financeiro=dados.responsavel_financeiro
    )
    db.add(vinculo)
    await db.commit()
    return {"mensagem": "Responsável vinculado com sucesso", "id": vinculo.id}

@router.get("/alunos/{aluno_id}/responsaveis")
async def listar_responsaveis_do_aluno(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os responsáveis vinculados a um aluno específico."""
    resultado = await db.execute(
        select(AlunoResponsavel).where(
            AlunoResponsavel.aluno_id == aluno_id,
            AlunoResponsavel.tenant_id == utilizador["tenant_id"]
        )
    )
    return resultado.scalars().all()
