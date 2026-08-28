from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import (
    EsqueciSenhaIn, LogoutIn, RedefinirSenhaIn, RefreshTokenIn, RefreshTokenOut, RegistoInicial, TokenResponse
)
from app.core.email import enviar_email, template_base
from app.core import fila_notificacoes
from app.core.rate_limiter import excedeu_limite
from app.core.security import obter_utilizador_atual
from app.cruds import auth as crud_auth

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação e Onboarding"])

# ==========================================
# LIMITADOR DE TENTATIVAS DE LOGIN (anti força-bruta)
# ==========================================
# A implementação em si (Redis partilhado entre instâncias, com
# fallback para memória local) vive em app/core/rate_limiter.py — só
# fica aqui o "o quê" (chave, limites), não o "como".
_LOGIN_MAX_TENTATIVAS = 5
_LOGIN_JANELA_SEGUNDOS = 60


async def _verificar_limite_login(chave: str) -> None:
    if await excedeu_limite(chave, _LOGIN_MAX_TENTATIVAS, _LOGIN_JANELA_SEGUNDOS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas tentativas de login. Tente novamente dentro de 1 minuto."
        )

@router.post("/registo", status_code=status.HTTP_201_CREATED)
async def registo_inicial_escola(dados: RegistoInicial):
    """Regista uma nova escola (Tenant) e o seu primeiro Gestor."""
    novo_tenant, novo_gestor = await crud_auth.registar_escola(dados)

    # E-mail de boas-vindas (best-effort — não atrasa a resposta nem
    # falha o registo se o SMTP falhar; retries automáticos via fila, ver
    # app/core/fila_notificacoes.py)
    await fila_notificacoes.agendar_email(
        enviar_email,
        destinatario=dados.email_gestor,
        assunto=f"Bem-vindo(a), {dados.nome_fantasia} já está na plataforma!",
        corpo_html=template_base(
            "Escola registada com sucesso!",
            f"""
            <p>Olá {dados.nome_gestor},</p>
            <p>A instituição <strong>{dados.nome_fantasia}</strong> foi criada com sucesso
            na plataforma de Gestão Académica.</p>
            <p>Já pode iniciar sessão com o e-mail <strong>{dados.email_gestor}</strong>
            para começar a configurar cursos, turmas e alunos.</p>
            """
        )
    )

    return {"mensagem": "Escola e conta de Gestor criadas com sucesso!"}


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Valida a hash da palavra-passe com o passlib e gera o access token
    (curto) + refresh token (mais duradouro, ver TokenResponse)."""
    ip_cliente = request.client.host if request.client else "desconhecido"
    await _verificar_limite_login(f"{ip_cliente}:{form_data.username}")

    return await crud_auth.autenticar(form_data.username, form_data.password, ip=ip_cliente, user_agent=request.headers.get("user-agent"))


@router.post("/refresh", response_model=RefreshTokenOut)
async def refresh(dados: RefreshTokenIn):
    """
    Troca o refresh token por um access token novo, sem pedir login
    outra vez — o front-end chama isto sozinho, em background, quando o
    access token (curto, ~20 min) expira. Ver
    cruds/auth.py::renovar_access_token para a rotação/deteção de roubo.
    """
    return await crud_auth.renovar_access_token(dados.refresh_token)


@router.post("/logout")
async def logout(dados: LogoutIn, utilizador: dict = Depends(obter_utilizador_atual)):
    """
    Logout com efeito real no back-end (Fase 5) — antes disto, "Sair do
    Sistema" só apagava o token no browser; ele continuava válido até
    expirar sozinho. Exige o access token atual (para saber qual jti
    revogar) e aceita opcionalmente o refresh_token, para revogar
    também essa sessão longa.
    """
    await crud_auth.terminar_sessao(dados.refresh_token, utilizador.get("jti"))
    return {"mensagem": "Sessão terminada."}


@router.post("/esqueci-senha")
async def esqueci_senha(dados: EsqueciSenhaIn, request: Request, background_tasks: BackgroundTasks):
    """
    Pede um link de redefinição de palavra-passe por e-mail.

    A resposta é sempre a mesma, exista ou não uma conta com este email
    (proteção contra enumeração de utilizadores) — e o trabalho todo
    (procurar o email, gerar o token, enviar o e-mail) corre em
    background, depois de já ter respondido: sem isto, o tempo de
    resposta em si denunciaria se o email existe (mais lento quando
    existe, porque manda e-mail; instantâneo quando não existe).
    """
    ip_cliente = request.client.host if request.client else "desconhecido"
    await _verificar_limite_login(f"reset:{ip_cliente}:{dados.email}")

    background_tasks.add_task(crud_auth.solicitar_redefinicao_senha, dados.email)

    return {"mensagem": "Se este email estiver registado, vai receber um link para redefinir a palavra-passe."}


@router.post("/redefinir-senha")
async def redefinir_senha(dados: RedefinirSenhaIn):
    """Valida o token recebido por e-mail e grava a nova palavra-passe."""
    await crud_auth.redefinir_senha(dados.token, dados.nova_senha)
    return {"mensagem": "Palavra-passe redefinida com sucesso. Já pode iniciar sessão."}
