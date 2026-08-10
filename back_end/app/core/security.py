from datetime import datetime, timedelta
from typing import Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import uuid
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 dia

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def criar_token_acesso(dados: Dict[str, Any]) -> str:
    """Gera o JWT contendo o tenant_id e escopo de acesso do utilizador."""
    copia_dados = dados.copy()
    expiracao = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    copia_dados.update({"exp": expiracao})
    return jwt.encode(copia_dados, SECRET_KEY, algorithm=ALGORITHM)

async def obter_utilizador_atual(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Middleware/Dependência que valida o JWT e extrai os dados do Tenant."""
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
        
        if tenant_id is None or usuario_id is None:
            raise credenciais_exception
            
        return {
            "usuario_id": uuid.UUID(usuario_id),
            "tenant_id": uuid.UUID(tenant_id),
            "perfil_acesso": perfil
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