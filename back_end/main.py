from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
from app.api.v1 import academico, auth, usuarios

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="API - SaaS Gestão Académica",
    description="Motor de regras e APIs da plataforma educacional.",
    version="1.0.0"
)


# 2. CONFIGURAÇÃO DE CORS (Essencial para o Angular comunicar com a API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"], # Permite apenas o nosso Front-end local
    allow_credentials=True,
    allow_methods=["*"], # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Permite o envio do cabeçalho de Authorization (Bearer Token)
)

# ==========================================
# MODELOS (Pydantic) para validação de dados
# ==========================================
class TenantCreate(BaseModel):
    nome_fantasia: str
    razao_social: Optional[str] = None
    nif: str

class TenantResponse(BaseModel):
    id: uuid.UUID
    nome_fantasia: str
    status: str

# ==========================================
# ENDPOINTS (Rotas da API)
# ==========================================

@app.post("/api/v1/admin/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def criar_tenant(tenant: TenantCreate):
    """
    Endpoint (Super Admin): Provisiona uma nova instituição de ensino.
    Na prática, aqui faríamos a inserção no PostgreSQL.
    """
    # Exemplo mockado do que o Back-end faria na Base de Dados
    novo_tenant_id = uuid.uuid4()
    
    # Aqui entraria a lógica SQLAlchemy/asyncpg para fazer o INSERT
    
    return {
        "id": novo_tenant_id,
        "nome_fantasia": tenant.nome_fantasia,
        "status": "ATIVO"
    }

# Registar os Endpoints (Revelar as rotas)
app.include_router(auth.router)
app.include_router(academico.router)
app.include_router(usuarios.router)
    
@app.get("/api/v1/health")
async def health_check():
    """Endpoint para verificar se a API está online."""
    return {"status": "ok", "mensagem": "Motor FastAPI a funcionar perfeitamente."}