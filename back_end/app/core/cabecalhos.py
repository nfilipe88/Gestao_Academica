"""Cabeçalhos de segurança em todas as respostas da API (o CSP da app vive no nginx).

Middleware ASGI puro, de propósito: o `@app.middleware("http")` do FastAPI
(BaseHTTPMiddleware) envolve cada pedido numa tarefa e num canal extra, o que
custa uma fatia visível do débito por processo; aqui só se acrescentam
cabeçalhos à mensagem `http.response.start`, sem tocar no corpo.
"""
from starlette.datastructures import MutableHeaders

_FIXOS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
)
_PREFIXO_SEM_CACHE = "/api/v1/auth"


class CabecalhosDeSegurancaMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        sem_cache = scope.get("path", "").startswith(_PREFIXO_SEM_CACHE)

        async def enviar(mensagem):
            if mensagem["type"] == "http.response.start":
                cabecalhos = MutableHeaders(scope=mensagem)
                for nome, valor in _FIXOS:
                    if nome not in cabecalhos:
                        cabecalhos[nome] = valor
                if sem_cache and "cache-control" not in cabecalhos:
                    cabecalhos["Cache-Control"] = "no-store"
            await send(mensagem)

        await self.app(scope, receive, enviar)
