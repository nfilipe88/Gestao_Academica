"""Limitador de tentativas genérico, com Redis quando disponível e
fallback automático para memória local quando não.

Porque isto importa: um limitador em memória (um dict do processo) só
conta as tentativas vistas por ESSE processo — com mais de um worker
uvicorn ou mais de uma instância do back-end atrás de um load balancer
(o normal em qualquer deploy a sério), cada um tem a sua própria
contagem, e um atacante distribui os pedidos entre eles para nunca
bater no limite. Com REDIS_URL configurada, a contagem passa a ser
partilhada por todas as instâncias, através do próprio Redis — sem
isso, mantém-se o comportamento anterior (só correto para uma única
instância), para o ambiente de desenvolvimento continuar a funcionar
sem precisar de correr Redis localmente.

Usa uma janela fixa (INCR + EXPIRE no primeiro incremento), não uma
janela deslizante como a versão em memória tinha — é o padrão habitual
para limitadores em Redis (mais barato, um INCR atómico em vez de
guardar e filtrar uma lista de timestamps) e a diferença prática é
irrelevante para este caso de uso (bloquear força bruta no login).
"""
import logging
import os
import time
from collections import defaultdict

logger = logging.getLogger("rate_limiter")

REDIS_URL = os.getenv("REDIS_URL")
_redis_cliente = None

if REDIS_URL:
    import redis.asyncio as redis_asyncio
    _redis_cliente = redis_asyncio.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    logger.info("Rate limiter: a usar Redis (%s instâncias podem correr em simultâneo em segurança).", "várias")
else:
    logger.warning(
        "Rate limiter: REDIS_URL não definida — a usar memória local. "
        "Só correto com UMA instância do back-end; ver .env.example."
    )

# Fallback em memória — mesma implementação (janela deslizante) que já
# existia só para o login, agora reutilizável para qualquer chave.
_memoria: dict[str, list[float]] = defaultdict(list)


async def excedeu_limite(chave: str, max_tentativas: int, janela_segundos: int) -> bool:
    """Regista uma tentativa para `chave` e devolve True se o limite já
    tiver sido excedido (a chamada que excede o limite já não conta
    como mais uma tentativa registada, para o bloqueio em si não
    prolongar a janela)."""
    if _redis_cliente is not None:
        try:
            return await _excedeu_limite_redis(chave, max_tentativas, janela_segundos)
        except Exception:
            # Redis em baixo não deve derrubar o login em si — falha
            # aberta para memória local desta instância, com aviso.
            logger.exception("Redis indisponível no rate limiter — a usar memória local para esta tentativa.")
            return _excedeu_limite_memoria(chave, max_tentativas, janela_segundos)
    return _excedeu_limite_memoria(chave, max_tentativas, janela_segundos)


async def _excedeu_limite_redis(chave: str, max_tentativas: int, janela_segundos: int) -> bool:
    chave_redis = f"ratelimit:{chave}"
    contagem = await _redis_cliente.incr(chave_redis)
    if contagem == 1:
        await _redis_cliente.expire(chave_redis, janela_segundos)
    return contagem > max_tentativas


def _excedeu_limite_memoria(chave: str, max_tentativas: int, janela_segundos: int) -> bool:
    agora = time.monotonic()
    tentativas = _memoria[chave]
    tentativas[:] = [t for t in tentativas if agora - t < janela_segundos]
    if len(tentativas) >= max_tentativas:
        return True
    tentativas.append(agora)
    return False
