"""
Fila de notificações (e-mail, SMS) com retries — substitui o antigo
"despachar via BackgroundTasks.add_task" (app/api/v1/financeiro.py e
outros): BackgroundTasks corre em memória, no próprio processo — se o
processo morrer entre o pedido responder e a tarefa correr (deploy,
OOM, crash) a notificação perde-se silenciosamente, sem nenhum
retry se o SMTP falhar uma vez por instabilidade passageira.

Com REDIS_URL configurada, cada notificação vira um trabalho numa
fila Redis (LIST) consumido por um worker in-process (ver
iniciar_worker/parar_worker, ligado ao lifespan em main.py); uma falha
a enviar reagenda o trabalho num ZSET "atrasado" com backoff
(30s / 2min / 10min) até 3 tentativas, depois desiste e regista em
log (dead-letter só nos logs — sem fila de erros dedicada nesta
primeira versão).

Sem REDIS_URL (mesma limitação já documentada para o resto — ver
rate_limiter.py/lock_distribuido.py/storage.py): fallback para envio
imediato e síncrono, sem retries, só correto com UMA instância.

`agendar_email`/`agendar_sms` são o ponto de entrada único usado em
toda a app (cruds/financeiro.py, cruds/admin.py, api/v1/comunicacoes.py,
etc.) — a MESMA função em qualquer contexto (dentro de um pedido HTTP
ou no scheduler.py), ao contrário do antigo padrão que precisava de
uma fábrica diferente consoante houvesse ou não um BackgroundTasks à
volta.
"""
import asyncio
import json
import logging
import os
import time
import uuid

from app.core.email import enviar_email
from app.core.sms import enviar_sms
from app.core import storage

logger = logging.getLogger("fila_notificacoes")

REDIS_URL = os.getenv("REDIS_URL")
_redis_cliente = None
if REDIS_URL:
    import redis.asyncio as redis_asyncio
    _redis_cliente = redis_asyncio.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
else:
    logger.warning(
        "REDIS_URL não definida — notificações (e-mail/SMS) são enviadas de "
        "imediato, sem fila nem retries. Só correto com UMA instância do back-end; ver .env.example."
    )

_FILA_PRINCIPAL = "fila:notificacoes"
_FILA_ATRASADA = "fila:notificacoes:atrasadas"
_ATRASOS_SEGUNDOS = [30, 120, 600]  # backoff entre tentativas: 30s, 2min, 10min

_tarefa_worker: asyncio.Task | None = None


async def _enviar_agora(job: dict) -> bool:
    """Executa mesmo o envio, independentemente de ter vindo da fila ou
    do fallback síncrono — devolve True/False como enviar_email/enviar_sms."""
    canal = job["canal"]
    dados = job["dados"]
    if canal == "email":
        anexo_bytes = None
        if dados.get("anexo_chave"):
            anexo_bytes = await storage.obter_ficheiro(dados["anexo_chave"])
        return await enviar_email(
            destinatario=dados["destinatario"], assunto=dados["assunto"], corpo_html=dados["corpo_html"],
            anexo_nome=dados.get("anexo_nome") if anexo_bytes else None,
            anexo_content_type=dados.get("anexo_content_type") if anexo_bytes else None,
            anexo_conteudo=anexo_bytes,
        )
    elif canal == "sms":
        return await enviar_sms(destinatario=dados["destinatario"], mensagem=dados["mensagem"])
    else:
        logger.error("Canal de notificação desconhecido na fila: %s", canal)
        return True  # não faz sentido reagendar um canal que não existe


async def _agendar(canal: str, dados: dict) -> None:
    if _redis_cliente is None:
        await _enviar_agora({"canal": canal, "dados": dados})
        return

    job = {"id": str(uuid.uuid4()), "canal": canal, "tentativa": 0, "dados": dados}
    try:
        await _redis_cliente.lpush(_FILA_PRINCIPAL, json.dumps(job))
    except Exception:
        # Falha aberta: Redis em baixo não pode significar "a escola não
        # recebe o e-mail" — cai para o envio síncrono desta vez.
        logger.exception("Falha ao enfileirar notificação (%s) — a enviar de imediato como reserva.", canal)
        await _enviar_agora(job)


async def agendar_email(func, **kwargs) -> None:
    """Assinatura compatível com o antigo `agendar_email(enviar_email,
    destinatario=..., assunto=..., corpo_html=...)` usado em toda a app
    — `func` não é usado para decidir o canal (é sempre e-mail aqui),
    só se mantém o parâmetro para não obrigar a mudar todas as chamadas
    existentes. anexo_chave (opcional): chave no storage a anexar,
    resolvida pelo worker só no momento do envio (nunca guardada em
    bytes na fila, para não fazer o Redis explodir de tamanho com
    ficheiros grandes repetidos por cada destinatário)."""
    await _agendar("email", kwargs)


async def agendar_sms(destinatario: str, mensagem: str) -> None:
    await _agendar("sms", {"destinatario": destinatario, "mensagem": mensagem})


async def _processar_um(job_json: str) -> None:
    job = json.loads(job_json)
    sucesso = await _enviar_agora(job)
    if sucesso:
        return

    tentativa = job.get("tentativa", 0)
    if tentativa >= len(_ATRASOS_SEGUNDOS):
        logger.error("Notificação (%s) desistida depois de %d tentativas: %s", job["canal"], tentativa + 1, job.get("dados", {}).get("destinatario"))
        return

    job["tentativa"] = tentativa + 1
    pronto_em = time.time() + _ATRASOS_SEGUNDOS[tentativa]
    try:
        await _redis_cliente.zadd(_FILA_ATRASADA, {json.dumps(job): pronto_em})
    except Exception:
        logger.exception("Falha ao reagendar notificação depois de uma tentativa falhada — fica perdida desta vez.")


async def _mover_atrasadas_prontas() -> None:
    """Move para a fila principal os trabalhos cujo atraso já passou —
    não é atómico (Redis pode duplicar um trabalho numa janela rara
    entre o ZRANGEBYSCORE e o ZREM), aceitável para notificações
    best-effort onde reenviar um e-mail a mais é inofensivo."""
    agora = time.time()
    prontos = await _redis_cliente.zrangebyscore(_FILA_ATRASADA, min=0, max=agora)
    for job_json in prontos:
        await _redis_cliente.zrem(_FILA_ATRASADA, job_json)
        await _redis_cliente.lpush(_FILA_PRINCIPAL, job_json)


async def _loop_worker() -> None:
    logger.info("Worker da fila de notificações arrancado.")
    while True:
        try:
            await _mover_atrasadas_prontas()
            resultado = await _redis_cliente.brpop(_FILA_PRINCIPAL, timeout=2)
            if resultado:
                _, job_json = resultado
                await _processar_um(job_json)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Erro inesperado no worker da fila de notificações — a continuar no próximo ciclo.")
            await asyncio.sleep(2)


def iniciar_worker() -> None:
    """Só arranca com Redis configurado — sem isso, agendar_email/
    agendar_sms já enviam de imediato, não há nada para consumir."""
    global _tarefa_worker
    if _redis_cliente is None or _tarefa_worker is not None:
        return
    _tarefa_worker = asyncio.create_task(_loop_worker())


async def parar_worker() -> None:
    global _tarefa_worker
    if _tarefa_worker is None:
        return
    _tarefa_worker.cancel()
    try:
        await _tarefa_worker
    except asyncio.CancelledError:
        pass
    _tarefa_worker = None
