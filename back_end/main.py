import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api.v1 import academico, admin, alunos, auth, comunicacoes, configuracoes, crm, diario, documentos, financeiro, horarios, indicadores, lms, matriculas, notificacoes, perfil, permissoes, portal, professores, propinas, tarefas, transferencias, usuarios
from app.core.scheduler import iniciar_scheduler, parar_scheduler
from app.core.monitorizacao import iniciar_sentry
from app.database.session import engine

# Antes de qualquer outra coisa, para também apanhar erros no arranque
# da própria app (import de routers, etc.).
iniciar_sentry()


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
# CORS_ALLOWED_ORIGINS: lista separada por vírgulas (ex.:
# "https://app.escola.pt,https://staging.escola.pt"). Sem esta variável
# definida, assume-se o dev server local do Angular — nunca deixar cair
# nesse default em produção (ver .env.example).
_origens_permitidas = [
    origem.strip()
    for origem in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:4200").split(",")
    if origem.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens_permitidas,
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
app.include_router(configuracoes.router)
app.include_router(lms.router)
app.include_router(perfil.router)
app.include_router(permissoes.router)
app.include_router(propinas.router)

@app.get("/api/v1/health")
async def health_check():
    """Confirma que a API está online E que consegue mesmo falar com a
    base de dados — usado pelo HEALTHCHECK do Docker/orquestrador para
    só marcar a instância como pronta quando as duas coisas forem
    verdade (só o processo estar vivo não chega: pode estar de pé mas
    incapaz de servir um único pedido real)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "base_de_dados": "ok"}
    except Exception as erro:
        return JSONResponse(
            status_code=503,
            content={"status": "erro", "base_de_dados": "inacessível", "detalhe": str(erro)},
        )
