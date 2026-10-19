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

from app.core import fila_notificacoes, revogacao, storage, validacao_ficheiros
from app.core.email import enviar_email, escapar, template_base
from app.cruds import auth as crud_auth, dois_fatores
from app.database.models import Usuario, Tenant, AssinaturaUsuario
from app.database.models_usuarios import RefreshToken
from app.core.security import criar_token_acesso, verificar_senha, gerar_hash_senha
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
        "dois_fatores_ativo": usuario.dois_fatores_ativo,
    }


async def atualizar_perfil(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, dados: PerfilUpdate) -> dict:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    email_anterior = None
    if dados.email != usuario.email:
        # O email é o login e o destino da recuperação de palavra-passe:
        # mudá-lo exige provar que se sabe a palavra-passe, não só ter
        # uma sessão aberta (ver PerfilUpdate.senha_atual).
        if not dados.senha_atual or not verificar_senha(dados.senha_atual, usuario.senha_hash):
            raise HTTPException(status_code=400, detail="Para alterar o email, confirme a sua palavra-passe atual.")
        email_existente = (await db.execute(
            select(Usuario).where(Usuario.email == dados.email, Usuario.id != usuario_id)
        )).scalars().first()
        if email_existente:
            raise HTTPException(status_code=400, detail="Este email já está em uso por outra conta.")
        email_anterior = usuario.email
        usuario.email = dados.email

    usuario.nome_completo = dados.nome_completo
    await db.commit()

    if email_anterior:
        # Aviso para o endereço ANTIGO — o único que o verdadeiro dono
        # ainda controla se a mudança não foi feita por ele.
        await fila_notificacoes.agendar_email(
            enviar_email, destinatario=email_anterior,
            assunto="O email da sua conta foi alterado",
            corpo_html=template_base(
                "Email da conta alterado",
                f"""
                <p>Olá {escapar(usuario.nome_completo)},</p>
                <p>O email de acesso da sua conta foi alterado para <strong>{escapar(usuario.email)}</strong>.
                A partir de agora, o login e a recuperação de palavra-passe usam esse endereço.</p>
                <p>Se não foi você a fazer esta alteração, contacte imediatamente a direção da escola.</p>
                """
            )
        )

    return await obter_perfil(db, tenant_id, usuario_id)


async def alterar_senha(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, dados: AlterarSenhaIn) -> dict:
    """Muda a palavra-passe e termina TODAS as sessões abertas (access
    tokens já emitidos e refresh tokens), em todos os dispositivos —
    mesmo critério de cruds/auth.py::redefinir_senha: quem muda a
    palavra-passe muitas vezes fá-lo por desconfiar que alguém a sabe,
    e essa pessoa não pode continuar com uma sessão aberta. A sessão de
    quem fez o pedido continua com um par de tokens novo, devolvido aqui."""
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="A palavra-passe atual está incorreta.")

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.usuario_id == usuario.id, RefreshToken.revogado.is_(False))
        .values(revogado=True)
    )
    await db.commit()
    await revogacao.revogar_usuario(usuario.id)

    access_token = criar_token_acesso(dados={
        "sub": str(usuario.id), "tenant_id": str(usuario.tenant_id), "perfil_acesso": usuario.perfil_acesso
    })
    refresh_token = await crud_auth._criar_refresh_token(db, usuario.tenant_id, usuario.id)
    await db.commit()

    await fila_notificacoes.agendar_email(
        enviar_email, destinatario=usuario.email,
        assunto="A sua palavra-passe foi alterada",
        corpo_html=template_base(
            "Palavra-passe alterada",
            f"""
            <p>Olá {escapar(usuario.nome_completo)},</p>
            <p>A palavra-passe da sua conta foi alterada e todas as outras sessões abertas foram terminadas.</p>
            <p>Se não foi você a fazer esta alteração, use o link "Esqueceu-se da palavra-passe?"
            no ecrã de login e contacte imediatamente a direção da escola.</p>
            """
        )
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


# ==========================================
# VERIFICAÇÃO EM DOIS PASSOS (código por e-mail no login — ver
# cruds/dois_fatores.py). Opcional: cada pessoa liga-a para si.
# ==========================================
async def _obter_usuario_com_senha(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, senha_atual: str) -> Usuario:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="A palavra-passe atual está incorreta.")
    return usuario


async def iniciar_ativacao_dois_fatores(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, senha_atual: str) -> dict:
    """Envia um código para o e-mail da conta: só fica ligada depois de
    confirmar que esse e-mail recebe mesmo os códigos — senão a pessoa
    ficava trancada fora da própria conta no login seguinte."""
    usuario = await _obter_usuario_com_senha(db, tenant_id, usuario_id, senha_atual)
    if usuario.dois_fatores_ativo:
        raise HTTPException(status_code=400, detail="A verificação em dois passos já está ativa.")
    desafio = await dois_fatores.criar_desafio(db, usuario, dois_fatores.ATIVAR)
    return {"desafio": desafio, "email_mascarado": dois_fatores.mascarar_email(usuario.email)}


async def confirmar_ativacao_dois_fatores(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, desafio: str, codigo: str) -> dict:
    dono = await dois_fatores.validar_codigo(db, desafio, codigo, dois_fatores.ATIVAR)
    if dono != usuario_id:
        raise HTTPException(status_code=400, detail="Este código expirou ou já não é válido. Peça um novo código.")
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    usuario.dois_fatores_ativo = True
    await db.commit()
    await _avisar_mudanca_dois_fatores(usuario, ativada=True)
    return await obter_perfil(db, tenant_id, usuario_id)


async def desativar_dois_fatores(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, senha_atual: str) -> dict:
    usuario = await _obter_usuario_com_senha(db, tenant_id, usuario_id, senha_atual)
    if usuario.dois_fatores_ativo:
        usuario.dois_fatores_ativo = False
        await db.commit()
        await _avisar_mudanca_dois_fatores(usuario, ativada=False)
    return await obter_perfil(db, tenant_id, usuario_id)


async def _avisar_mudanca_dois_fatores(usuario: Usuario, ativada: bool) -> None:
    estado = "ativada" if ativada else "desativada"
    await fila_notificacoes.agendar_email(
        enviar_email, destinatario=usuario.email,
        assunto=f"Verificação em dois passos {estado}",
        corpo_html=template_base(
            f"Verificação em dois passos {estado}",
            f"""
            <p>Olá {escapar(usuario.nome_completo)},</p>
            <p>A verificação em dois passos da sua conta foi <strong>{estado}</strong>.
            {"A partir de agora, cada início de sessão pede também um código enviado para este e-mail." if ativada else
             "A partir de agora, o início de sessão volta a pedir só a palavra-passe."}</p>
            <p>Se não foi você a fazer esta alteração, mude a sua palavra-passe imediatamente
            e contacte a direção da escola.</p>
            """
        )
    )


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
    content_type = await validacao_ficheiros.validar_upload(conteudo, _TIPOS_ASSINATURA_ACEITES, "PNG, JPEG ou WebP", nome_original)
    if len(conteudo) > _TAMANHO_MAXIMO_ASSINATURA:
        raise HTTPException(status_code=400, detail="A assinatura não pode passar de 5 MB.")

    await db.execute(
        update(AssinaturaUsuario)
        .where(AssinaturaUsuario.tenant_id == tenant_id, AssinaturaUsuario.usuario_id == usuario_id, AssinaturaUsuario.ativa.is_(True))
        .values(ativa=False)
    )

    chave = storage.gerar_chave(tenant_id, "assinatura_pessoal", nome_original, content_type)
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
