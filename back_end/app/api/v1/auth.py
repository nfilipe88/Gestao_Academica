import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.session import AsyncSessionLocal # Usamos sessão limpa (sem RLS forçado ainda)
from app.database.models import Usuario, Tenant
from app.schemas.auth_schemas import RegistoInicial, TokenResponse
from app.core.security import verificar_senha, gerar_hash_senha, criar_token_acesso

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
async def registo_inicial_escola(dados: RegistoInicial):
    """
    Endpoint para registo de uma nova escola (Tenant) e do seu primeiro Gestor.
    A operação é transacional: ou cria tudo, ou reverte tudo.
    """
    async with AsyncSessionLocal() as db:
        # 1. Verificar se o NIF ou Email já existem
        nif_existente = await db.execute(select(Tenant).where(Tenant.nif == dados.nif))
        if nif_existente.scalars().first():
            raise HTTPException(status_code=400, detail="Este NIF já está registado.")
            
        email_existente = await db.execute(select(Usuario).where(Usuario.email == dados.email_gestor))
        if email_existente.scalars().first():
            raise HTTPException(status_code=400, detail="Este email já está em uso.")

        try:
            # 2. Criar a Instituição (Tenant)
            novo_tenant = Tenant(
                nome_fantasia=dados.nome_fantasia,
                nif=dados.nif,
                status="ATIVO"
            )
            db.add(novo_tenant)
            await db.flush() # Envia para o Postgres para obter o ID do Tenant, mas não faz commit final

            # 3. Criar o Utilizador Gestor com palavra-passe encriptada (passlib)
            hash_senha = gerar_hash_senha(dados.palavra_passe)
            novo_gestor = Usuario(
                tenant_id=novo_tenant.id,
                nome_completo=dados.nome_gestor,
                email=dados.email_gestor,
                senha_hash=hash_senha,
                perfil_acesso="GESTOR"
            )
            db.add(novo_gestor)
            
            # 4. Confirmar a transação
            await db.commit()
            
            return {"mensagem": "Escola e conta de Gestor criadas com sucesso!"}
            
        except Exception as e:
            await db.rollback() # Se algo falhar, cancela a criação do Tenant e do Utilizador
            raise HTTPException(status_code=500, detail=f"Erro ao processar registo: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de Login Padrão.
    Valida a hash da palavra-passe com o passlib e gera o JWT.
    """
    ip_cliente = request.client.host if request.client else "desconhecido"
    _verificar_limite_login(f"{ip_cliente}:{form_data.username}")

    async with AsyncSessionLocal() as db:
        # 1. Procurar o utilizador pelo email (username)
        resultado = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
        usuario = resultado.scalars().first()

        # 2. Validar se o utilizador existe e se a palavra-passe está correta
        if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou palavra-passe incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Verificar o status do Tenant (Bloqueio por Inadimplência do SaaS)
        # Opcional, mas altamente recomendado no Nível 2
        tenant = await db.execute(select(Tenant).where(Tenant.id == usuario.tenant_id))
        tenant_status = tenant.scalars().first().status
        if tenant_status != "ATIVO":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O acesso da sua instituição encontra-se suspenso. Contacte o suporte."
            )

        # 4. Construir o Payload do JWT com os dados para o RLS
        dados_token = {
            "sub": str(usuario.id),
            "tenant_id": str(usuario.tenant_id),
            "perfil_acesso": usuario.perfil_acesso
        }

        # 5. Devolver o Token
        token_jwt = criar_token_acesso(dados=dados_token)

        return {
            "access_token": token_jwt,
            "token_type": "bearer",
            "utilizador": {
                "id": str(usuario.id),
                "nome_completo": usuario.nome_completo,
                "perfil_acesso": usuario.perfil_acesso,
                "tenant_id": str(usuario.tenant_id)
            }
        }