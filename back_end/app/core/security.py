from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import uuid
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

from app.core import revogacao

load_dotenv()

# Configuração do passlib para usar bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_texto_limpo: str, senha_hash: str) -> bool:
    """Verifica se a senha digitada corresponde ao hash guardado na base de dados."""
    return pwd_context.verify(senha_texto_limpo, senha_hash)

def gerar_hash_senha(senha: str) -> str:
    """Gera um hash seguro para gravar novos utilizadores."""
    return pwd_context.hash(senha)

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY não encontrada. Crie um ficheiro .env na raiz do back_end "
        "com base no .env.example."
    )
ALGORITHM = "HS256"
# Curto de propósito (era 24h) — reduz a janela de risco se um token
# for roubado (ex.: XSS, já que o front-end guarda o token em
# localStorage). Sessões longas continuam a funcionar sem pedir login
# outra vez: o front-end troca automaticamente por um novo access token
# usando o refresh token, de duração muito maior mas revogável (ver
# REFRESH_TOKEN_EXPIRE_DIAS abaixo e app/api/v1/auth.py::POST /auth/refresh).
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "20"))
REFRESH_TOKEN_EXPIRE_DIAS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DIAS", "7"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def criar_token_acesso(dados: Dict[str, Any]) -> str:
    """Gera o JWT contendo o tenant_id e escopo de acesso do utilizador.

    "iat" (issued-at) e "jti" (id único deste token, usado só para o
    revogar individualmente no logout) são o que torna a revogação de
    sessão possível (ver app/core/revogacao.py) — um JWT não pode ser
    "apagado" depois de emitido, só comparado com um registo de "isto
    foi revogado depois deste momento"."""
    copia_dados = dados.copy()
    agora = datetime.now(timezone.utc)
    expiracao = agora + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    copia_dados.update({"exp": expiracao, "iat": agora, "jti": str(uuid.uuid4())})
    return jwt.encode(copia_dados, SECRET_KEY, algorithm=ALGORITHM)

async def obter_utilizador_atual(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Middleware/Dependência que valida o JWT, confirma que não foi
    revogado entretanto (escola suspensa, utilizador desativado, perfil
    mudado, ou logout deste token específico — ver
    app/core/revogacao.py) e extrai os dados do Tenant."""
    credenciais_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id: str = payload.get("tenant_id")
        usuario_id: str = payload.get("sub")
        perfil: str = payload.get("perfil_acesso")
        jti: str | None = payload.get("jti")
        iat: float | None = payload.get("iat")

        if tenant_id is None or usuario_id is None:
            raise credenciais_exception

        if iat is not None and await revogacao.esta_revogado(tenant_id, usuario_id, jti, float(iat)):
            raise credenciais_exception

        return {
            "usuario_id": uuid.UUID(usuario_id),
            "tenant_id": uuid.UUID(tenant_id),
            "perfil_acesso": perfil,
            "jti": jti,
        }
    except JWTError:
        raise credenciais_exception


def exigir_perfil(*perfis_permitidos: str):
    """
    Fábrica de dependência para RBAC (Controlo de Acesso Baseado em
    Funções): bloqueia o endpoint com 403 se o perfil_acesso do
    utilizador autenticado não estiver entre os permitidos.

    Uso: Depends(exigir_perfil("GESTOR", "SECRETARIA"))

    Substitui Depends(obter_utilizador_atual) nos endpoints que devem
    ficar restritos — a autenticação (JWT válido) continua a ser
    exigida da mesma forma, isto só acrescenta a verificação de perfil.
    """
    async def verificar(utilizador: Dict[str, Any] = Depends(obter_utilizador_atual)) -> Dict[str, Any]:
        if utilizador["perfil_acesso"] not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito a: {', '.join(perfis_permitidos)}."
            )
        return utilizador
    return verificar


# Usado no lugar de obter_utilizador_atual nas leituras "abertas a
# qualquer utilizador autenticado" de módulos de uso interno (Académico,
# Alunos, Comunicações, Diário, Horários, Matrículas, Professores) — até
# ao Portal (ALUNO/RESPONSAVEL) existir, "qualquer autenticado" só podia
# significar "qualquer funcionário da escola", porque só GESTOR/
# SECRETARIA/PROFESSOR tinham login. Agora que ALUNO/RESPONSAVEL também
# podem autenticar-se, isto deixou de ser verdade: essas leituras
# devolvem dados de outras famílias/turmas, para além dos próprios
# educandos. O Portal (app/api/v1/portal.py, app/cruds/portal.py) é o
# único sítio onde ALUNO/RESPONSAVEL leem os seus próprios dados.
exigir_perfil_staff = exigir_perfil("GESTOR", "SECRETARIA", "PROFESSOR")