"""
Acesso a dados de Autenticação e Onboarding.

Ao contrário dos restantes módulos, estas funções abrem a própria
sessão (AsyncSessionLocalSistema) em vez de receber uma via
Depends(obter_sessao_db) — nesta fase (registo/login) ainda não há um
utilizador autenticado para extrair o tenant_id do JWT, e ambas as
operações são inerentemente cross-tenant: procurar um email para fazer
login não sabe a priori a que escola ele pertence (o email é único em
toda a plataforma, não só dentro de um tenant), e registar uma escola
nova está a criar o próprio tenant, antes de existir qualquer
"tenant atual" para o RLS filtrar. Por isso usam o role app_sistema
(bypassrls) em vez do app_tenant usado pelo resto da app — ver
app/database/session.py.

O limitador de tentativas de login (anti força-bruta) fica na camada
de API — depende do IP do pedido HTTP, não é uma preocupação de
acesso a dados.
"""
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select

from app.database.session import AsyncSessionLocalSistema
from app.database.models import Usuario, Tenant
from app.database.models_diario import TipoAvaliacaoConfig
from app.database.models_usuarios import LoginHistorico, PasswordResetToken, RefreshToken
from app.core.security import verificar_senha, gerar_hash_senha, criar_token_acesso, REFRESH_TOKEN_EXPIRE_DIAS
from app.core.email import enviar_email, template_base
from app.core import fila_notificacoes, revogacao
from app.schemas.auth import RegistoInicial

# Janela de validade do link de recuperação de senha — curta de
# propósito (é enviado por e-mail, um canal que pode ficar exposto por
# mais tempo do que uma sessão normal).
RESET_TOKEN_EXPIRE_MINUTES = 30

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200").rstrip("/")


def _hash_token(token: str) -> str:
    """Mesma lógica de Usuario.senha_hash: só o hash fica na base de dados, o token em texto limpo só existe no e-mail."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def registar_escola(dados: RegistoInicial) -> tuple[Tenant, Usuario]:
    """
    Cria a Instituição (Tenant) e o seu primeiro Gestor. A operação é
    transacional: ou cria tudo, ou reverte tudo.
    """
    async with AsyncSessionLocalSistema() as db:
        nif_existente = await db.execute(select(Tenant).where(Tenant.nif == dados.nif))
        if nif_existente.scalars().first():
            raise HTTPException(status_code=400, detail="Este NIF já está registado.")

        email_existente = await db.execute(select(Usuario).where(Usuario.email == dados.email_gestor))
        if email_existente.scalars().first():
            raise HTTPException(status_code=400, detail="Este email já está em uso.")

        try:
            novo_tenant = Tenant(
                nome_fantasia=dados.nome_fantasia,
                nif=dados.nif,
                status="ATIVO"
            )
            db.add(novo_tenant)
            await db.flush()  # Envia para o Postgres para obter o ID do Tenant, mas não faz commit final

            hash_senha = gerar_hash_senha(dados.palavra_passe)
            novo_gestor = Usuario(
                tenant_id=novo_tenant.id,
                nome_completo=dados.nome_gestor,
                email=dados.email_gestor,
                senha_hash=hash_senha,
                perfil_acesso="GESTOR"
            )
            db.add(novo_gestor)

            # Seed dos tipos de avaliação por omissão (CONTINUA/PROVA) —
            # sem isto, uma escola registada pelo fluxo normal fica sem
            # nenhum TipoAvaliacaoConfig, e o Diário bloqueia qualquer
            # lançamento "por Avaliação" (ver
            # cruds/diario.py::_validar_e_obter_tipo_avaliacao). A migração
            # cfe1a4e36025 fez este seed uma única vez, só para os tenants
            # que já existiam nessa altura — replica-se aqui o mesmo par
            # (nome, requer_agendamento) para toda escola nova.
            db.add(TipoAvaliacaoConfig(
                tenant_id=novo_tenant.id, nome="CONTINUA", requer_agendamento=False, ativo=True
            ))
            db.add(TipoAvaliacaoConfig(
                tenant_id=novo_tenant.id, nome="PROVA", requer_agendamento=True, ativo=True
            ))

            await db.commit()
            return novo_tenant, novo_gestor
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()  # Se algo falhar, cancela a criação do Tenant e do Utilizador
            raise HTTPException(status_code=500, detail=f"Erro ao processar registo: {str(e)}")


async def _criar_refresh_token(db, tenant_id, usuario_id) -> str:
    """Gera um refresh token novo, grava só o hash (mesmo princípio de
    Usuario.senha_hash/PasswordResetToken) e devolve o valor em texto
    limpo, que só existe aqui — nunca mais é recuperável depois disto."""
    token_bruto = secrets.token_urlsafe(48)
    db.add(RefreshToken(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        token_hash=_hash_token(token_bruto),
        expira_em=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DIAS),
    ))
    return token_bruto


async def _registar_login_e_alertar(db, usuario: Usuario, ip: str | None, user_agent: str | None) -> None:
    """Best-effort: uma falha aqui nunca deve impedir o login. Alerta só
    quando este IP nunca apareceu antes para este utilizador — o
    primeiro login de sempre não gera alerta (não há "IP habitual"
    ainda para comparar)."""
    if not ip:
        return
    try:
        ja_visto = (await db.execute(
            select(LoginHistorico.id).where(LoginHistorico.usuario_id == usuario.id, LoginHistorico.ip == ip).limit(1)
        )).first()
        historico_existe = (await db.execute(
            select(LoginHistorico.id).where(LoginHistorico.usuario_id == usuario.id).limit(1)
        )).first()

        db.add(LoginHistorico(tenant_id=usuario.tenant_id, usuario_id=usuario.id, ip=ip, user_agent=(user_agent or "")[:255]))

        if historico_existe and not ja_visto:
            await fila_notificacoes.agendar_email(
                enviar_email, destinatario=usuario.email,
                assunto="Novo login detetado na sua conta",
                corpo_html=template_base(
                    "Novo login detetado",
                    f"""
                    <p>Olá {usuario.nome_completo},</p>
                    <p>Detetámos um login na sua conta a partir de um endereço IP que nunca tinha usado antes: <strong>{ip}</strong>.</p>
                    <p>Se foi você, pode ignorar este e-mail. Se não reconhece este acesso, mude a sua palavra-passe
                    imediatamente (link "Esqueceu-se da palavra-passe?" no ecrã de login) e contacte a direção da escola.</p>
                    """
                )
            )
    except Exception:
        logging.getLogger("auth").exception("Falha ao registar/alertar sobre login de %s — não impede o login.", usuario.email)


async def autenticar(email: str, palavra_passe: str, ip: str | None = None, user_agent: str | None = None) -> dict:
    """
    Valida a hash da palavra-passe com o passlib, confirma que a escola
    (Tenant) não está suspensa, e gera o access token (JWT, curto) + o
    refresh token (na BD, revogável, mais duradouro — ver
    app/core/security.py e a docstring de RefreshToken).
    """
    async with AsyncSessionLocalSistema() as db:
        resultado = await db.execute(select(Usuario).where(Usuario.email == email))
        usuario = resultado.scalars().first()

        if not usuario or not verificar_senha(palavra_passe, usuario.senha_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou palavra-passe incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Suspensão individual (RBAC — Núcleo Multi-Tenant): distinta da
        # suspensão da escola inteira abaixo. Ver
        # cruds/usuarios.py::alterar_estado_ativo.
        if not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O seu acesso foi suspenso. Contacte a direção da escola."
            )

        # Bloqueio por Inadimplência do SaaS (Nível 2)
        tenant = await db.execute(select(Tenant).where(Tenant.id == usuario.tenant_id))
        tenant_status = tenant.scalars().first().status
        if tenant_status != "ATIVO":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O acesso da sua instituição encontra-se suspenso. Contacte o suporte."
            )

        dados_token = {
            "sub": str(usuario.id),
            "tenant_id": str(usuario.tenant_id),
            "perfil_acesso": usuario.perfil_acesso
        }
        token_jwt = criar_token_acesso(dados=dados_token)
        refresh_token = await _criar_refresh_token(db, usuario.tenant_id, usuario.id)
        await _registar_login_e_alertar(db, usuario, ip, user_agent)
        await db.commit()

        return {
            "access_token": token_jwt,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "utilizador": {
                "id": str(usuario.id),
                "nome_completo": usuario.nome_completo,
                "perfil_acesso": usuario.perfil_acesso,
                "tenant_id": str(usuario.tenant_id)
            }
        }


async def renovar_access_token(refresh_token_bruto: str) -> dict:
    """
    Troca um refresh token válido por um access token novo — chamado
    pelo front-end sozinho, em background, quando o access token
    (curto) expira, sem obrigar a pessoa a fazer login outra vez.

    Rotação: o refresh token usado fica marcado (revogado=True) e um
    novo é emitido — nunca é reutilizável. Continuar a receber o MESMO
    refresh token depois disto só pode significar que alguém copiou um
    token antigo; por isso, se o token já usado voltar a aparecer,
    trata-se como sinal de roubo e revoga TODOS os refresh tokens
    desse utilizador (obriga a autenticar-se de novo em todos os
    dispositivos) — não só o pedido é recusado.
    """
    credenciais_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada. Inicie sessão novamente.")

    async with AsyncSessionLocalSistema() as db:
        token_hash = _hash_token(refresh_token_bruto)
        registo = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalars().first()
        if not registo:
            raise credenciais_exception

        if registo.revogado:
            # Reuso de um token já rodado — possível roubo (ver docstring acima).
            await db.execute(
                RefreshToken.__table__.update()
                .where(RefreshToken.usuario_id == registo.usuario_id, RefreshToken.revogado == False)  # noqa: E712
                .values(revogado=True)
            )
            await revogacao.revogar_usuario(registo.usuario_id)
            await db.commit()
            raise credenciais_exception

        if registo.expira_em.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise credenciais_exception

        usuario = (await db.execute(select(Usuario).where(Usuario.id == registo.usuario_id))).scalars().first()
        if not usuario or not usuario.ativo:
            raise credenciais_exception
        tenant = (await db.execute(select(Tenant).where(Tenant.id == usuario.tenant_id))).scalars().first()
        if not tenant or tenant.status != "ATIVO":
            raise credenciais_exception

        registo.revogado = True
        novo_refresh_token = await _criar_refresh_token(db, usuario.tenant_id, usuario.id)
        token_jwt = criar_token_acesso(dados={
            "sub": str(usuario.id), "tenant_id": str(usuario.tenant_id), "perfil_acesso": usuario.perfil_acesso
        })
        await db.commit()

        return {"access_token": token_jwt, "refresh_token": novo_refresh_token, "token_type": "bearer"}


async def terminar_sessao(refresh_token_bruto: str | None, jti_access_token: str | None) -> None:
    """Logout com efeito real no back-end (Fase 5) — antes disto, "Sair
    do Sistema" só apagava o token no browser; o token continuava
    válido no back-end até expirar sozinho. Revoga só ESTA sessão (este
    par access+refresh token), não todos os dispositivos da pessoa."""
    if jti_access_token:
        await revogacao.revogar_jti(jti_access_token)
    if refresh_token_bruto:
        async with AsyncSessionLocalSistema() as db:
            token_hash = _hash_token(refresh_token_bruto)
            registo = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))).scalars().first()
            if registo and not registo.revogado:
                registo.revogado = True
                await db.commit()


async def solicitar_redefinicao_senha(email: str) -> None:
    """
    Gera um token de recuperação e envia o link por e-mail (best-effort,
    em background — ver api/v1/auth.py).

    Deliberadamente NUNCA revela ao chamador se o email existe ou não —
    a resposta da API é sempre a mesma mensagem genérica, mesmo aqui
    dentro esta função não devolve nada nem levanta exceção por email
    desconhecido. Sem isto, o endpoint seria um oráculo para descobrir
    que emails têm conta na plataforma (enumeração de utilizadores).
    """
    async with AsyncSessionLocalSistema() as db:
        usuario = (await db.execute(select(Usuario).where(Usuario.email == email))).scalars().first()
        if not usuario or not usuario.ativo:
            return  # silêncio de propósito — ver docstring

        # Invalida quaisquer tokens anteriores ainda não usados: só o
        # link mais recente pedido deve funcionar.
        tokens_antigos = (await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.usuario_id == usuario.id, PasswordResetToken.usado == False  # noqa: E712
            )
        )).scalars().all()
        for antigo in tokens_antigos:
            antigo.usado = True

        token_bruto = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            token_hash=_hash_token(token_bruto),
            expira_em=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        ))
        await db.commit()

        link = f"{FRONTEND_URL}/redefinir-senha?token={token_bruto}"
        await fila_notificacoes.agendar_email(
            enviar_email,
            destinatario=usuario.email,
            assunto="Redefinir a sua palavra-passe",
            corpo_html=template_base(
                "Pedido de redefinição de palavra-passe",
                f"""
                <p>Olá {usuario.nome_completo},</p>
                <p>Recebemos um pedido para redefinir a palavra-passe da sua conta.
                Clique no link abaixo para escolher uma nova palavra-passe — o link
                expira em {RESET_TOKEN_EXPIRE_MINUTES} minutos:</p>
                <p><a href="{link}" style="color:#2563eb;">Redefinir palavra-passe</a></p>
                <p>Se não foi você a pedir isto, ignore este e-mail — a sua
                palavra-passe atual continua válida.</p>
                """
            )
        )


async def redefinir_senha(token: str, nova_senha: str) -> None:
    """Valida o token (hash + expiração + não usado) e grava a nova palavra-passe."""
    async with AsyncSessionLocalSistema() as db:
        registo = (await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
        )).scalars().first()

        token_invalido = HTTPException(status_code=400, detail="Este link de redefinição é inválido ou já expirou.")
        if not registo or registo.usado:
            raise token_invalido
        if registo.expira_em.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise token_invalido

        usuario = (await db.execute(select(Usuario).where(Usuario.id == registo.usuario_id))).scalars().first()
        if not usuario:
            raise token_invalido

        usuario.senha_hash = gerar_hash_senha(nova_senha)
        registo.usado = True
        # Uma palavra-passe só é redefinida por "esqueci-me" quando há
        # razão para desconfiar da anterior — todas as sessões (access
        # tokens já emitidos e refresh tokens na BD) deviam morrer já,
        # em todos os dispositivos, não só na próxima vez que expirarem sozinhas.
        await db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.usuario_id == usuario.id, RefreshToken.revogado == False)  # noqa: E712
            .values(revogado=True)
        )
        await db.commit()
        await revogacao.revogar_usuario(usuario.id)

        await fila_notificacoes.agendar_email(
            enviar_email,
            destinatario=usuario.email,
            assunto="A sua palavra-passe foi alterada",
            corpo_html=template_base(
                "Palavra-passe alterada",
                f"""
                <p>Olá {usuario.nome_completo},</p>
                <p>A palavra-passe da sua conta foi alterada com sucesso através do
                link de recuperação.</p>
                <p>Se não foi você, contacte a direção da sua escola imediatamente.</p>
                """
            )
        )
