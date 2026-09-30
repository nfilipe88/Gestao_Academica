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
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.database.models import Usuario, Tenant, AssinaturaUsuario
from app.core.security import verificar_senha, gerar_hash_senha
from app.schemas.perfil import PerfilUpdate, AlterarSenhaIn

# Assinatura pessoal: mesmos limites já usados para a fotografia de
# perfil do aluno (app/cruds/alunos.py) — é o mesmo tipo de imagem
# pequena (retrato/traço), não um documento em alta resolução.
_TIPOS_ASSINATURA_ACEITES = {"image/png", "image/jpeg", "image/webp"}
_TAMANHO_MAXIMO_ASSINATURA = 5 * 1024 * 1024  # 5 MB


async def obter_perfil(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> dict:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()

    assinatura_ativa = (await db.execute(
        select(AssinaturaUsuario.id).where(
            AssinaturaUsuario.usuario_id == usuario_id, AssinaturaUsuario.tenant_id == tenant_id, AssinaturaUsuario.ativa.is_(True)
        )
    )).scalars().first()

    return {
        "id": usuario.id,
        "nome_completo": usuario.nome_completo,
        "email": usuario.email,
        "perfil_acesso": usuario.perfil_acesso,
        "tenant_id": usuario.tenant_id,
        "nome_instituicao": tenant.nome_fantasia if tenant else "",
        "data_criacao": usuario.data_criacao,
        "tem_assinatura_pessoal": assinatura_ativa is not None,
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


# ==========================================
# ASSINATURA PESSOAL (para documentos PDF emitidos pelo próprio — ver
# app/core/assinaturas.py) — mesmo padrão versionado de FotoPerfilAluno:
# nunca apaga a anterior, arquiva-a (ativa=False) e insere uma nova
# linha. Sem restrição de perfil de propósito (ver app/api/v1/perfil.py)
# — um ALUNO/RESPONSAVEL a enviar uma é inofensivo, nunca é lida em
# nenhum PDF; o filtro real é visual, no frontend.
# ==========================================
async def enviar_assinatura_pessoal(
    db: AsyncSession, tenant_id, usuario_id: uuid.UUID, nome_original: str, content_type: str, conteudo: bytes
) -> None:
    if content_type not in _TIPOS_ASSINATURA_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato não aceite ({content_type}). Use PNG, JPEG ou WebP.")
    if len(conteudo) > _TAMANHO_MAXIMO_ASSINATURA:
        raise HTTPException(status_code=400, detail="A assinatura não pode passar de 5 MB.")

    await db.execute(
        update(AssinaturaUsuario)
        .where(AssinaturaUsuario.tenant_id == tenant_id, AssinaturaUsuario.usuario_id == usuario_id, AssinaturaUsuario.ativa.is_(True))
        .values(ativa=False)
    )

    chave = storage.gerar_chave(tenant_id, "assinatura_pessoal", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    db.add(AssinaturaUsuario(tenant_id=tenant_id, usuario_id=usuario_id, chave_storage=chave, ativa=True))
    await db.commit()


async def remover_assinatura_pessoal(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> None:
    await db.execute(
        update(AssinaturaUsuario)
        .where(AssinaturaUsuario.tenant_id == tenant_id, AssinaturaUsuario.usuario_id == usuario_id, AssinaturaUsuario.ativa.is_(True))
        .values(ativa=False)
    )
    await db.commit()


async def obter_assinatura_pessoal_url(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> str:
    assinatura = (await db.execute(
        select(AssinaturaUsuario).where(
            AssinaturaUsuario.tenant_id == tenant_id, AssinaturaUsuario.usuario_id == usuario_id, AssinaturaUsuario.ativa.is_(True)
        )
    )).scalars().first()
    if not assinatura:
        raise HTTPException(status_code=404, detail="Ainda não tem assinatura pessoal configurada.")
    url = await storage.obter_data_uri(assinatura.chave_storage)
    if not url:
        raise HTTPException(status_code=404, detail="Ficheiro da assinatura já não está disponível.")
    return url
