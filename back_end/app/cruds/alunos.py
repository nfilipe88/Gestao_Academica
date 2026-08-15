"""Acesso a dados de Alunos, Responsáveis e o vínculo entre eles.

O envio de e-mail de notificação (RN de vínculo) fica na camada de API,
não aqui — depende de BackgroundTasks, que é um mecanismo do FastAPI,
não uma preocupação de acesso a dados.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.models import Usuario
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.core.security import gerar_hash_senha
from app.core.paginacao import paginar
from app.schemas.alunos import AlunoCreate, CriarAcessoRequest, ResponsavelCreate, VincularResponsavel


# ==========================================
# RESOLUÇÃO DE ACESSO (que aluno_id um login ALUNO/RESPONSAVEL pode ver)
#
# Extraído aqui (em vez de duplicado) porque tanto o Portal como os
# Pedidos de Documentos precisam da mesma pergunta: "a que aluno_id(s)
# este login tem direito?". Aluno é o dono natural desta regra.
# ==========================================
async def resolver_meus_alunos(db: AsyncSession, tenant_id, utilizador: dict) -> list[uuid.UUID]:
    perfil = utilizador.get("perfil_acesso")
    if perfil == "ALUNO":
        aluno_id = (await db.execute(
            select(Aluno.id).where(Aluno.usuario_id == utilizador["usuario_id"], Aluno.tenant_id == tenant_id)
        )).scalar_one_or_none()
        return [aluno_id] if aluno_id else []
    if perfil == "RESPONSAVEL":
        responsavel_id = (await db.execute(
            select(ResponsavelFinanceiroLegal.id).where(
                ResponsavelFinanceiroLegal.usuario_id == utilizador["usuario_id"],
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if not responsavel_id:
            return []
        ids = (await db.execute(
            select(AlunoResponsavel.aluno_id).where(AlunoResponsavel.responsavel_id == responsavel_id)
        )).scalars().all()
        return list(ids)
    return []


async def garantir_aluno_permitido(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> Aluno:
    permitidos = await resolver_meus_alunos(db, tenant_id, utilizador)
    if aluno_id not in permitidos:
        raise HTTPException(status_code=403, detail="Sem acesso a este aluno.")
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
    return aluno


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


async def listar_alunos(db: AsyncSession, tenant_id, page: int, page_size: int) -> dict:
    query = select(Aluno).where(Aluno.tenant_id == tenant_id).order_by(Aluno.nome_completo)
    return await paginar(db, query, page, page_size)


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


async def listar_responsaveis(db: AsyncSession, tenant_id, page: int, page_size: int) -> dict:
    query = select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.tenant_id == tenant_id).order_by(ResponsavelFinanceiroLegal.nome_completo)
    return await paginar(db, query, page, page_size)


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


# ==========================================
# ACESSO AO PORTAL (login próprio para Aluno/Responsável)
# ==========================================
async def _criar_acesso(db: AsyncSession, tenant_id, dados: CriarAcessoRequest, perfil_acesso: str, nome_completo: str) -> Usuario:
    """Cria o Usuario (perfil_acesso=ALUNO/RESPONSAVEL) que o registo de Aluno/Responsável vai passar a referenciar."""
    email_existente = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if email_existente.scalars().first():
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    novo_usuario = Usuario(
        tenant_id=tenant_id,
        nome_completo=nome_completo,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.palavra_passe),
        perfil_acesso=perfil_acesso,
    )
    db.add(novo_usuario)
    await db.flush()
    return novo_usuario


async def criar_acesso_aluno(db: AsyncSession, tenant_id, aluno_id: uuid.UUID, dados: CriarAcessoRequest) -> Usuario:
    aluno = (await db.execute(
        select(Aluno).where(Aluno.id == aluno_id, Aluno.tenant_id == tenant_id)
    )).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
    if aluno.usuario_id:
        raise HTTPException(status_code=400, detail="Este aluno já tem acesso ao Portal.")

    try:
        novo_usuario = await _criar_acesso(db, tenant_id, dados, "ALUNO", aluno.nome_completo)
        aluno.usuario_id = novo_usuario.id
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    await db.refresh(novo_usuario)
    return novo_usuario


async def criar_acesso_responsavel(db: AsyncSession, tenant_id, responsavel_id: uuid.UUID, dados: CriarAcessoRequest) -> Usuario:
    responsavel = (await db.execute(
        select(ResponsavelFinanceiroLegal).where(
            ResponsavelFinanceiroLegal.id == responsavel_id, ResponsavelFinanceiroLegal.tenant_id == tenant_id
        )
    )).scalars().first()
    if not responsavel:
        raise HTTPException(status_code=404, detail="Responsável não encontrado na sua instituição.")
    if responsavel.usuario_id:
        raise HTTPException(status_code=400, detail="Este responsável já tem acesso ao Portal.")

    try:
        novo_usuario = await _criar_acesso(db, tenant_id, dados, "RESPONSAVEL", responsavel.nome_completo)
        responsavel.usuario_id = novo_usuario.id
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    await db.refresh(novo_usuario)
    return novo_usuario
