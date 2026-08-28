"""Lock distribuído mínimo (SET NX EX no Redis) — usado pelos jobs
agendados (scheduler.py) para nunca correrem em duplicado quando há
mais de uma instância do back-end no ar. Com mais de uma instância e
sem isto, cada uma corre o seu próprio APScheduler in-process e todas
disparam à mesma hora (CronTrigger), duplicando e-mails de lembrete e
reprocessando a régua de cobrança várias vezes.

Sem REDIS_URL configurada, assume-se uma única instância (mesma
limitação documentada em rate_limiter.py) e o lock é sempre "obtido"
localmente, sem nenhuma coordenação real.
"""
import logging
import os

logger = logging.getLogger("lock_distribuido")

REDIS_URL = os.getenv("REDIS_URL")
_redis_cliente = None
if REDIS_URL:
    import redis.asyncio as redis_asyncio
    _redis_cliente = redis_asyncio.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)


async def tentar_obter_lock(chave: str, ttl_segundos: int) -> bool:
    """Tenta reservar `chave` por ttl_segundos — devolve True só para a
    primeira instância a conseguir (SET ... NX), False para todas as
    outras que tentem durante essa janela. O TTL é a proteção contra o
    lock ficar preso para sempre se a instância que o obteve morrer a
    meio (ex.: processo morto/OOM) sem o largar — não há "largar"
    explícito, o lock expira sozinho.
    """
    if _redis_cliente is None:
        return True  # sem Redis, sem coordenação — assume-se 1 instância só.
    try:
        obtido = await _redis_cliente.set(f"lock:{chave}", "1", nx=True, ex=ttl_segundos)
        return bool(obtido)
    except Exception:
        # Falha aberta: mais vale arriscar correr o job em duplicado
        # numa janela rara de Redis em baixo do que nunca o correr.
        logger.exception("Redis indisponível no lock distribuído — a assumir que esta instância pode correr o job.")
        return True
