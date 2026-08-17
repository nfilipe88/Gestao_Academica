"""
Área de Perfil (self-service) — ver app/schemas/perfil.py.

Ao contrário de app/cruds/usuarios.py (o Gestor gere OUTRAS contas via
usuario_id explícito), aqui o alvo é sempre o próprio utilizador
autenticado — nenhuma função recebe um usuario_id de fora, todas
recebem o dict `utilizador` extraído do JWT (Depends(obter_utilizador_atual))
e operam sobre `utilizador["usuario_id"]`. Isto por si só garante que
ninguém consegue ler/editar a conta de outra pessoa por aqui, mesmo que
uma validação de RBAC fosse esquecida num endpoint novo no futuro.

Usa a sessão normal (obter_sessao_db, role app_tenant, RLS aplicado) —
ao contrário de auth.py (login/registo/recuperação de senha), aqui já
há um utilizador autenticado com tenant_id conhecido, não é uma
operação pré-tenant.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Usuario, Tenant
from app.core.security import verificar_senha, gerar_hash_senha
from app.schemas.perfil import PerfilUpdate, AlterarSenhaIn


async def obter_perfil(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> dict:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()

    return {
        "id": usuario.id,
        "nome_completo": usuario.nome_completo,
        "email": usuario.email,
        "perfil_acesso": usuario.perfil_acesso,
        "tenant_id": usuario.tenant_id,
        "nome_instituicao": tenant.nome_fantasia if tenant else "",
        "data_criacao": usuario.data_criacao,
    }


async def atualizar_perfil(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, dados: PerfilUpdate) -> dict:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    if dados.email != usuario.email:
        email_existente = (await db.execute(
            select(Usuario).where(Usuario.email == dados.email, Usuario.id != usuario_id)
        )).scalars().first()
        if email_existente:
            raise HTTPException(status_code=400, detail="Este email já está em uso por outra conta.")
        usuario.email = dados.email

    usuario.nome_completo = dados.nome_completo
    await db.commit()

    return await obter_perfil(db, tenant_id, usuario_id)


async def alterar_senha(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, dados: AlterarSenhaIn) -> None:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="A palavra-passe atual está incorreta.")

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    await db.commit()
