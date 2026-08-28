"""
SMS/WhatsApp transacional (best-effort) — camada pluggável, sem
integração com nenhum gateway específico: o mercado angolano não tem
um único fornecedor óbvio (Twilio não opera bem em Angola; um gateway
local de SMS/WhatsApp Business API exige uma conta comercial e
credenciais reais que não existem nesta instalação), por isso a
integração real fica para quando a escola/plataforma escolher um
fornecedor — o que está aqui é a abstração pronta a ligar.

Provedor "webhook" genérico: faz um POST HTTPS simples
({"para": destinatario, "mensagem": mensagem}, Bearer token) para
SMS_WEBHOOK_URL — a maioria dos gateways (Twilio, africa's talking,
gateways locais de operadoras) consegue ser colocada atrás disto com
um pequeno serviço intermediário, ou o próprio gateway pode expor um
endpoint compatível diretamente. Sem SMS_WEBHOOK_URL configurada, o
envio fica só registado nos logs — a aplicação continua a funcionar
normalmente (mesmo espírito de app/core/email.py: nunca bloqueia nem
cancela a operação principal por causa disto).
"""
import logging
import os

import httpx

logger = logging.getLogger("sms")

SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL")
SMS_WEBHOOK_TOKEN = os.getenv("SMS_WEBHOOK_TOKEN")


async def enviar_sms(destinatario: str, mensagem: str) -> bool:
    """Devolve True se o envio foi aceite pelo gateway, False caso
    contrário (e regista o motivo nos logs) — nunca levanta exceção."""
    if not SMS_WEBHOOK_URL:
        logger.warning(
            "SMS_WEBHOOK_URL não configurado — SMS para %s NÃO foi enviado. Mensagem: %s",
            destinatario, mensagem
        )
        return False

    cabecalhos = {"Authorization": f"Bearer {SMS_WEBHOOK_TOKEN}"} if SMS_WEBHOOK_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=10) as cliente:
            resposta = await cliente.post(SMS_WEBHOOK_URL, json={"para": destinatario, "mensagem": mensagem}, headers=cabecalhos)
            resposta.raise_for_status()
        logger.info("SMS enviado para %s via webhook.", destinatario)
        return True
    except Exception:
        logger.exception("Falha ao enviar SMS para %s via webhook.", destinatario)
        return False
