"""Acesso a dados de Professores e Alocação (Professor <-> Turma <-> Disciplina).

O envio de e-mail de boas-vindas ao Professor fica na camada de API
(depende de BackgroundTasks do FastAPI).
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.models import Usuario
from app.database.models_academico import Disciplina, Turma
from app.database.models_pessoas import Professor
from app.database.models_diario import ProfessorTurmaDisciplina
from app.core.security import gerar_hash_senha
from app.schemas.professores import AlocacaoCreate, ProfessorCreate


async def criar_professor(db: AsyncSession, tenant_id, dados: ProfessorCreate) -> tuple[Professor, Usuario]:
    """
    Cria a conta de Professor: um Usuario novo (perfil_acesso=PROFESSOR,
    com login próprio) e o registo de Professor associado, numa única
    transação — ou cria tudo, ou reverte tudo.
    """
    email_existente = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if email_existente.scalars().first():
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    try:
        novo_usuario = Usuario(
            tenant_id=tenant_id,
            nome_completo=dados.nome_completo,
            email=dados.email,
            senha_hash=gerar_hash_senha(dados.palavra_passe),
            perfil_acesso="PROFESSOR"
        )
        db.add(novo_usuario)
        await db.flush()  # Obter o id do Usuario sem fazer commit final

        novo_professor = Professor(
            tenant_id=tenant_id,
            usuario_id=novo_usuario.id,
            formacao_academica=dados.formacao_academica
        )
        db.add(novo_professor)
        await db.commit()
        await db.refresh(novo_professor)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar professor: {str(e)}")

    return novo_professor, novo_usuario


async def listar_professores(db: AsyncSession, tenant_id) -> list[dict]:
    resultado = await db.execute(
        select(Professor, Usuario.nome_completo, Usuario.email)
        .join(Usuario, Usuario.id == Professor.usuario_id)
        .where(Professor.tenant_id == tenant_id)
    )
    return [
        {
            "id": professor.id,
            "usuario_id": professor.usuario_id,
            "nome_completo": nome_completo,
            "email": email,
            "formacao_academica": professor.formacao_academica,
            "data_criacao": professor.data_criacao,
        }
        for professor, nome_completo, email in resultado.all()
    ]


# ==========================================
# ALOCAÇÃO (Professor <-> Turma <-> Disciplina)
# ==========================================
async def alocar_professor(db: AsyncSession, tenant_id, professor_id: uuid.UUID, dados: AlocacaoCreate) -> ProfessorTurmaDisciplina:
    """Define que este professor lecciona esta disciplina nesta turma."""
    professor = (await db.execute(
        select(Professor).where(Professor.id == professor_id, Professor.tenant_id == tenant_id)
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=404, detail="Professor não encontrado na sua instituição.")

    turma = (await db.execute(
        select(Turma).where(Turma.id == dados.turma_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == dados.disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")

    ja_existe = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.professor_id == professor_id,
            ProfessorTurmaDisciplina.turma_id == dados.turma_id,
            ProfessorTurmaDisciplina.disciplina_id == dados.disciplina_id
        )
    )).scalars().first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Este professor já está alocado a esta disciplina nesta turma.")

    nova_alocacao = ProfessorTurmaDisciplina(
        tenant_id=tenant_id,
        professor_id=professor_id,
        turma_id=dados.turma_id,
        disciplina_id=dados.disciplina_id
    )
    db.add(nova_alocacao)
    await db.commit()
    return nova_alocacao


async def listar_minhas_alocacoes(db: AsyncSession, utilizador: dict) -> list[dict]:
    """
    Lista as alocações (turma+disciplina) do professor autenticado — usadas
    pelo Diário de Classe para saber a que turmas/disciplinas ele tem acesso.
    Gestor/Secretaria recebem todas as alocações da escola.
    """
    tenant_id = utilizador["tenant_id"]

    query = (
        select(ProfessorTurmaDisciplina, Turma.nome_codigo, Disciplina.nome)
        .join(Turma, Turma.id == ProfessorTurmaDisciplina.turma_id)
        .join(Disciplina, Disciplina.id == ProfessorTurmaDisciplina.disciplina_id)
        .where(ProfessorTurmaDisciplina.tenant_id == tenant_id)
    )

    if utilizador["perfil_acesso"] == "PROFESSOR":
        professor = (await db.execute(
            select(Professor).where(Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == tenant_id)
        )).scalars().first()
        if not professor:
            return []
        query = query.where(ProfessorTurmaDisciplina.professor_id == professor.id)

    resultado = await db.execute(query)
    return [
        {
            "id": alocacao.id,
            "professor_id": alocacao.professor_id,
            "turma_id": alocacao.turma_id,
            "nome_turma": nome_turma,
            "disciplina_id": alocacao.disciplina_id,
            "nome_disciplina": nome_disciplina,
        }
        for alocacao, nome_turma, nome_disciplina in resultado.all()
    ]
