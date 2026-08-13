"""Acesso a dados de Alunos, Responsáveis e o vínculo entre eles.

O envio de e-mail de notificação (RN de vínculo) fica na camada de API,
não aqui — depende de BackgroundTasks, que é um mecanismo do FastAPI,
não uma preocupação de acesso a dados.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.schemas.alunos import AlunoCreate, ResponsavelCreate, VincularResponsavel


async def criar_aluno(db: AsyncSession, tenant_id, dados: AlunoCreate) -> Aluno:
    ja_existe = await db.execute(
        select(Aluno).where(Aluno.tenant_id == tenant_id, Aluno.matricula_interna == dados.matricula_interna)
    )
    if ja_existe.scalars().first():
        raise HTTPException(status_code=400, detail="Já existe um aluno com esta matrícula interna.")

    novo_aluno = Aluno(
        tenant_id=tenant_id,
        matricula_interna=dados.matricula_interna,
        nome_completo=dados.nome_completo,
        data_nascimento=dados.data_nascimento,
        numero_documento=dados.numero_documento
    )
    db.add(novo_aluno)
    await db.commit()
    await db.refresh(novo_aluno)
    return novo_aluno


async def listar_alunos(db: AsyncSession, tenant_id) -> list[Aluno]:
    resultado = await db.execute(select(Aluno).where(Aluno.tenant_id == tenant_id))
    return resultado.scalars().all()


async def criar_responsavel(db: AsyncSession, tenant_id, dados: ResponsavelCreate) -> ResponsavelFinanceiroLegal:
    novo_responsavel = ResponsavelFinanceiroLegal(
        tenant_id=tenant_id,
        nome_completo=dados.nome_completo,
        telefone_contato=dados.telefone_contato,
        numero_documento=dados.numero_documento,
        email=dados.email
    )
    db.add(novo_responsavel)
    await db.commit()
    await db.refresh(novo_responsavel)
    return novo_responsavel


async def listar_responsaveis(db: AsyncSession, tenant_id) -> list[ResponsavelFinanceiroLegal]:
    resultado = await db.execute(
        select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.tenant_id == tenant_id)
    )
    return resultado.scalars().all()


async def vincular_responsavel(
    db: AsyncSession, tenant_id, aluno_id: uuid.UUID, dados: VincularResponsavel
) -> tuple[AlunoResponsavel, Aluno, ResponsavelFinanceiroLegal]:
    """Vincula um responsável já existente a um aluno (RN: um aluno pode ter vários responsáveis).

    Devolve também o Aluno e o Responsável para quem chamar poder
    compor o e-mail de notificação sem uma segunda ida à base de dados.
    """
    aluno_db = await db.execute(select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id))
    aluno = aluno_db.scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    responsavel_db = await db.execute(
        select(ResponsavelFinanceiroLegal).where(
            ResponsavelFinanceiroLegal.id == dados.responsavel_id,
            ResponsavelFinanceiroLegal.tenant_id == tenant_id
        )
    )
    responsavel = responsavel_db.scalars().first()
    if not responsavel:
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
        tenant_id=tenant_id,
        aluno_id=aluno_id,
        responsavel_id=dados.responsavel_id,
        tipo_parentesco=dados.tipo_parentesco,
        responsavel_financeiro=dados.responsavel_financeiro
    )
    db.add(vinculo)
    await db.commit()
    return vinculo, aluno, responsavel


async def listar_responsaveis_do_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> list[AlunoResponsavel]:
    resultado = await db.execute(
        select(AlunoResponsavel).where(AlunoResponsavel.aluno_id == aluno_id, AlunoResponsavel.tenant_id == tenant_id)
    )
    return resultado.scalars().all()
