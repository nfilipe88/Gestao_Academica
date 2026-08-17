import time
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import EsqueciSenhaIn, RedefinirSenhaIn, RegistoInicial, TokenResponse
from app.core.email import enviar_email, template_base
from app.cruds import auth as crud_auth

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação e Onboarding"])

# ==========================================
# LIMITADOR DE TENTATIVAS DE LOGIN (anti força-bruta)
# ==========================================
# Implementação simples em memória: suficiente para um único processo/dev.
# Em produção com múltiplos workers/instâncias, substituir por um limitador
# partilhado (ex.: slowapi + Redis), senão cada worker conta à parte.
_LOGIN_TENTATIVAS: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_TENTATIVAS = 5
_LOGIN_JANELA_SEGUNDOS = 60


def _verificar_limite_login(chave: str) -> None:
    agora = time.monotonic()
    tentativas = _LOGIN_TENTATIVAS[chave]
    tentativas[:] = [t for t in tentativas if agora - t < _LOGIN_JANELA_SEGUNDOS]
    if len(tentativas) >= _LOGIN_MAX_TENTATIVAS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas tentativas de login. Tente novamente dentro de 1 minuto."
        )
    tentativas.append(agora)

@router.post("/registo", status_code=status.HTTP_201_CREATED)
async def registo_inicial_escola(dados: RegistoInicial, background_tasks: BackgroundTasks):
    """Regista uma nova escola (Tenant) e o seu primeiro Gestor."""
    novo_tenant, novo_gestor = await crud_auth.registar_escola(dados)

    # E-mail de boas-vindas (best-effort, em background — não atrasa a
    # resposta nem falha o registo se o SMTP falhar)
    background_tasks.add_task(
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
    """Valida a hash da palavra-passe com o passlib e gera o JWT."""
    ip_cliente = request.client.host if request.client else "desconhecido"
    _verificar_limite_login(f"{ip_cliente}:{form_data.username}")

    return await crud_auth.autenticar(form_data.username, form_data.password)


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
    _verificar_limite_login(f"reset:{ip_cliente}:{dados.email}")

    background_tasks.add_task(crud_auth.solicitar_redefinicao_senha, dados.email)

    return {"mensagem": "Se este email estiver registado, vai receber um link para redefinir a palavra-passe."}


@router.post("/redefinir-senha")
async def redefinir_senha(dados: RedefinirSenhaIn):
    """Valida o token recebido por e-mail e grava a nova palavra-passe."""
    await crud_auth.redefinir_senha(dados.token, dados.nova_senha)
    return {"mensagem": "Palavra-passe redefinida com sucesso. Já pode iniciar sessão."}
