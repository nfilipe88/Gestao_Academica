"""Verificação de Google reCAPTCHA v3 — proteção silenciosa (sem
puzzle visual, só um score 0.0-1.0 de "isto parece humano") para os
dois endpoints públicos mais expostos a automação: registo de escola
(POST /auth/registo) e captação de leads do CRM (POST
/public/{tenant_id}/leads).

Sem RECAPTCHA_SECRET_KEY configurada, a verificação é ignorada (mesmo
padrão de REDIS_URL em rate_limiter.py) — assim o ambiente de
desenvolvimento e os testes automatizados continuam a funcionar sem
precisar de chaves reais nem de rede para a Google.
"""
import logging
import os

import httpx

logger = logging.getLogger("recaptcha")

# Chave pública, servida ao frontend via GET /api/v1/public/config —
# só a SECRET_KEY é sensível (usada aqui, no servidor, para validar o
# token junto da Google).
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

# Abaixo deste score, a Google considera o pedido suspeito de ser bot.
# 0.5 é o valor de referência recomendado pela própria documentação do
# reCAPTCHA v3 para um primeiro corte, sem histórico de tráfego real
# ainda para afinar.
_LIMIAR_SCORE = 0.5
_URL_VERIFICACAO = "https://www.google.com/recaptcha/api/siteverify"

if not RECAPTCHA_SECRET_KEY:
    logger.warning(
        "reCAPTCHA: RECAPTCHA_SECRET_KEY não definida — verificação "
        "desativada (só correto em desenvolvimento/testes; ver .env.example)."
    )


async def token_e_valido(token: str | None, ip_cliente: str | None = None) -> bool:
    """True se o token vier de um pedido com score aceitável — ou se a
    verificação estiver desativada (sem chave configurada, dev/testes).
    """
    if not RECAPTCHA_SECRET_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as cliente:
            dados = {"secret": RECAPTCHA_SECRET_KEY, "response": token}
            if ip_cliente:
                dados["remoteip"] = ip_cliente
            resp = await cliente.post(_URL_VERIFICACAO, data=dados)
            resultado = resp.json()
    except Exception:
        # A Google em baixo (ou lenta) não pode derrubar o registo/lead
        # em si — falha aberta, o rate limiting já cobre o essencial do
        # abuso mesmo sem esta camada extra. Mesmo espírito do rate
        # limiter com Redis em baixo (ver core/rate_limiter.py).
        logger.exception("Falha a contactar o reCAPTCHA — a aceitar o pedido sem verificação.")
        return True
    aceite = bool(resultado.get("success")) and float(resultado.get("score", 0)) >= _LIMIAR_SCORE
    if not aceite:
        # Log intencional (não só em erro) — o score em si é o dado que
        # mais interessa para afinar _LIMIAR_SCORE mais tarde, com
        # tráfego real, sem ter de adivinhar porque é que um pedido
        # legítimo pode ter ficado bloqueado.
        logger.warning("reCAPTCHA recusou um pedido: %s", resultado)
    return aceite
