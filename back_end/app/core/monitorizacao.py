"""Rastreio de erros em produção (Sentry) — opcional, só ativa se
SENTRY_DSN estiver definida no .env. Sem isto configurado, um erro em
produção só é descoberto quando alguém grepa os logs à mão depois de
uma escola se queixar; com isto, aparece agregado e com stack trace
assim que acontece.
"""
import logging
import os

logger = logging.getLogger("monitorizacao")

SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "development")
# DSN do Angular — projeto Sentry separado de propósito (ver ConfigPublicaOut
# em app/schemas/publico.py, devolvido por GET /api/v1/public/config). Nunca
# usar SENTRY_DSN (o do backend) aqui: o Sentry aceita um DSN de cliente
# embutido no JS de qualquer site que o tenha — nada impede outra origem de
# o usar para enviar eventos falsos, por isso convém não ser o mesmo projeto
# que recebe os erros reais do servidor.
# "or None" (não só os.getenv sozinho): uma linha em branco no .env
# ("SENTRY_DSN_FRONTEND=") dá string vazia, não None — o contrato desta
# variável (ver ConfigPublicaOut) promete None quando desligado.
SENTRY_DSN_FRONTEND = os.getenv("SENTRY_DSN_FRONTEND") or None


def iniciar_sentry() -> None:
    """Chamado uma vez, no arranque da aplicação (ver main.py) — antes
    de app = FastAPI(...), para também apanhar erros no próprio arranque."""
    if not SENTRY_DSN:
        logger.info("Sentry não configurado (SENTRY_DSN em branco) — erros só ficam nos logs locais.")
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # Amostragem de performance/traces baixa de propósito — o
        # objetivo principal aqui é captura de erros, não profiling
        # detalhado de latência (isso é uma decisão separada, mais
        # cara, para outra altura).
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("Sentry ativo (ambiente=%s).", SENTRY_ENVIRONMENT)
