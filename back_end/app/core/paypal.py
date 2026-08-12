"""
Cliente mínimo para a PayPal Orders API v2 (intent=CAPTURE).

Fluxo usado por este projeto (ver app/api/v1/financeiro.py):
1. criar_order()   -> POST /v2/checkout/orders            (gerar-cobranca)
2. o responsável aprova o pagamento no site do PayPal (approve_url)
3. capturar_order() -> POST /v2/checkout/orders/{id}/capture (capturar)

O Webhook (verificar_assinatura_webhook) é um mecanismo de reconciliação
adicional (RN03 do documento) — a confirmação "principal" já acontece no
passo 3, chamado pelo front-end assim que o PayPal redireciona de volta
com sucesso. O webhook garante que a fatura fica paga mesmo que o
utilizador feche a janela antes do redirecionamento voltar a correr.

Nunca imprime nem regista o Client Secret nos logs.
"""
import base64
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("paypal")

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID")  # opcional; sem isto o webhook não valida a assinatura

BASE_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE != "live" else "https://api-m.paypal.com"


class PayPalNaoConfigurado(Exception):
    """Levantada quando PAYPAL_CLIENT_ID/SECRET não estão definidos no .env."""


def _exigir_credenciais():
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise PayPalNaoConfigurado(
            "PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET não configurados no .env do back-end."
        )


async def _obter_token_acesso() -> str:
    """OAuth2 client_credentials — um token novo por operação (simples; o
    volume desta aplicação não justifica cache/renovação do token)."""
    _exigir_credenciais()
    credenciais = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()

    async with httpx.AsyncClient(timeout=15) as client:
        resposta = await client.post(
            f"{BASE_URL}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credenciais}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        resposta.raise_for_status()
        return resposta.json()["access_token"]


async def criar_order(valor: str, referencia: str, descricao: str, return_url: str, cancel_url: str) -> dict:
    """
    Cria uma PayPal Order (intent=CAPTURE) para o valor indicado (string
    com 2 casas decimais, ex: "511.65"). Devolve o payload bruto da
    resposta do PayPal — quem chama extrai o id e o link "approve".
    """
    token = await _obter_token_acesso()
    async with httpx.AsyncClient(timeout=15) as client:
        resposta = await client.post(
            f"{BASE_URL}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": referencia,
                    "description": descricao[:127],
                    "amount": {"currency_code": "EUR", "value": valor},
                }],
                "application_context": {
                    "brand_name": "SaaS Gestão Académica",
                    "user_action": "PAY_NOW",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                },
            },
        )
        resposta.raise_for_status()
        return resposta.json()


async def capturar_order(order_id: str) -> dict:
    """Efetiva a cobrança de uma Order já aprovada pelo pagador. Devolve o payload bruto."""
    token = await _obter_token_acesso()
    async with httpx.AsyncClient(timeout=15) as client:
        resposta = await client.post(
            f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        resposta.raise_for_status()
        return resposta.json()


async def verificar_assinatura_webhook(headers: dict, corpo_bruto: bytes, webhook_id: str | None = None) -> bool:
    """
    RN03 — valida que o webhook realmente veio do PayPal (evita que
    alguém simule um pagamento chamando a rota pública diretamente).
    Usa o endpoint oficial de verificação do PayPal em vez de
    reimplementar a verificação criptográfica localmente.
    """
    webhook_id = webhook_id or PAYPAL_WEBHOOK_ID
    if not webhook_id:
        logger.warning("PAYPAL_WEBHOOK_ID não configurado — verificação de assinatura do webhook ignorada.")
        return False

    import json
    token = await _obter_token_acesso()
    async with httpx.AsyncClient(timeout=15) as client:
        resposta = await client.post(
            f"{BASE_URL}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "transmission_id": headers.get("paypal-transmission-id"),
                "transmission_time": headers.get("paypal-transmission-time"),
                "cert_url": headers.get("paypal-cert-url"),
                "auth_algo": headers.get("paypal-auth-algo"),
                "transmission_sig": headers.get("paypal-transmission-sig"),
                "webhook_id": webhook_id,
                "webhook_event": json.loads(corpo_bruto),
            },
        )
        resposta.raise_for_status()
        return resposta.json().get("verification_status") == "SUCCESS"
