from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import academico, admin, alunos, auth, comunicacoes, crm, diario, documentos, financeiro, horarios, indicadores, matriculas, notificacoes, portal, professores, tarefas, transferencias, usuarios
from app.core.scheduler import iniciar_scheduler, parar_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranca o agendador interno (régua de cobrança diária — RN04) e
    # desliga-o de forma limpa quando a aplicação termina.
    iniciar_scheduler()
    yield
    parar_scheduler()


# Inicialização da aplicação FastAPI
app = FastAPI(
    title="API - SaaS Gestão Académica",
    description="Motor de regras e APIs da plataforma educacional.",
    version="1.0.0",
    lifespan=lifespan,
)

# CONFIGURAÇÃO DE CORS (Essencial para o Angular comunicar com a API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"], # Permite apenas o nosso Front-end local
    allow_credentials=True,
    allow_methods=["*"], # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Permite o envio do cabeçalho de Authorization (Bearer Token)
)

# ==========================================
# ENDPOINTS (Rotas da API)
# ==========================================
# Nota: a criação de tenants é feita em POST /api/v1/auth/registo
# (app/api/v1/auth.py::registo_inicial_escola), que já persiste na base de
# dados. Removido daqui o endpoint mockado que duplicava esta rota sem
# autenticação e sem gravar nada.

app.include_router(auth.router)
app.include_router(academico.router)
app.include_router(alunos.router)
app.include_router(matriculas.router)
app.include_router(professores.router)
app.include_router(comunicacoes.router)
app.include_router(diario.router)
app.include_router(financeiro.router)
app.include_router(financeiro.router_webhooks)
app.include_router(crm.router)
app.include_router(crm.router_publico)
app.include_router(horarios.router)
app.include_router(portal.router)
app.include_router(admin.router)
app.include_router(tarefas.router)
app.include_router(indicadores.router)
app.include_router(notificacoes.router)
app.include_router(documentos.router)
app.include_router(transferencias.router)
app.include_router(usuarios.router)

@app.get("/api/v1/health")
async def health_check():
    """Endpoint para verificar se a API está online."""
    return {"status": "ok", "mensagem": "Motor FastAPI a funcionar perfeitamente."}
