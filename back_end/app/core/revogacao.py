"""
Revogação de sessão — resolve duas limitações que estavam documentadas
e aceites no código desde sempre (ver app/database/models.py::Usuario.ativo
e Tenant.status): suspender uma escola, desativar um utilizador, ou
mudar o perfil de acesso de alguém só tinha efeito real quando o JWT
dessa pessoa expirasse sozinho — até 24h depois. Um "Sair do Sistema"
também só apagava o token no browser; o token em si continuava válido
no back-end até expirar.

Como o JWT é stateless (a app não guarda sessões, só valida a
assinatura), não há como "apagar" um token já emitido — a técnica
aqui é registar QUANDO algo mudou, e comparar com QUANDO o token foi
emitido (claim "iat"): um token emitido antes da revogação passa a ser
inválido, mesmo com assinatura e "exp" corretos.

Duas granularidades:
- revogar_tenant/revogar_usuario: todos os tokens emitidos antes de
  agora ficam inválidos — usado quando a escola é suspensa, o
  utilizador é desativado, ou o seu perfil de acesso muda (o token
  antigo continua a carregar o perfil ERRADO nas claims).
- revogar_jti: só ESTE token fica inválido (via um identificador único
  por token, a claim "jti") — usado no logout, sem obrigar todas as
  outras sessões/dispositivos da mesma pessoa a terminar sessão.

Com REDIS_URL configurada, a revogação é visível imediatamente por
todas as instâncias do back-end. Sem Redis, cai para um registo em
memória local (mesma limitação já documentada para rate_limiter.py/
lock_distribuido.py/fila_notificacoes.py — só correto com UMA
instância; com mais do que uma, cada uma só sabe das revogações feitas
nela própria).
"""
import logging
import os
import time

logger = logging.getLogger("revogacao")

REDIS_URL = os.getenv("REDIS_URL")
_redis_cliente = None
if REDIS_URL:
    import redis.asyncio as redis_asyncio
    _redis_cliente = redis_asyncio.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
else:
    logger.warning(
        "REDIS_URL não definida — revogação de sessão (suspensão/desativação/logout) só "
        "fica visível na instância que a fez. Só correto com UMA instância do back-end; ver .env.example."
    )

# TTL das chaves de revogação no Redis — não precisa de durar mais do
# que o token mais antigo que ainda poderia estar em circulação
# (refresh tokens rodam a cada uso, mas um access token isolado pode
# viver até ACCESS_TOKEN_EXPIRE_MINUTES). Uma folga generosa evita
# apagar a revogação cedo demais só porque alguém mudou a duração do
# token no .env sem atualizar isto.
_TTL_REVOGACAO_SEGUNDOS = 7 * 24 * 3600  # 7 dias

# Fallback em memória (só válido dentro do próprio processo).
_revogados_tenant: dict[str, float] = {}
_revogados_usuario: dict[str, float] = {}
_jtis_revogados: set[str] = set()


async def _marcar(chave: str, cache_local: dict[str, float]) -> None:
    agora = time.time()
    cache_local[chave] = agora
    if _redis_cliente is not None:
        try:
            await _redis_cliente.set(f"revogado:{chave}", agora, ex=_TTL_REVOGACAO_SEGUNDOS)
        except Exception:
            logger.exception("Falha ao gravar a revogação de '%s' no Redis — fica só em memória local nesta instância.", chave)


async def revogar_tenant(tenant_id) -> None:
    await _marcar(f"tenant:{tenant_id}", _revogados_tenant)


async def revogar_usuario(usuario_id) -> None:
    await _marcar(f"usuario:{usuario_id}", _revogados_usuario)


async def revogar_jti(jti: str) -> None:
    _jtis_revogados.add(jti)
    if _redis_cliente is not None:
        try:
            await _redis_cliente.set(f"revogado:jti:{jti}", "1", ex=_TTL_REVOGACAO_SEGUNDOS)
        except Exception:
            logger.exception("Falha ao gravar a revogação do token (jti) no Redis — fica só em memória local nesta instância.")


async def _revogado_desde(chave: str, cache_local: dict[str, float]) -> float | None:
    """Devolve o timestamp da revogação mais recente para esta chave, ou
    None se nunca foi revogada — combina Redis (fonte de verdade entre
    instâncias) com o cache local (cobre o próprio processo mesmo que o
    Redis fique indisponível a meio)."""
    valor_local = cache_local.get(chave)
    if _redis_cliente is None:
        return valor_local
    try:
        valor_redis = await _redis_cliente.get(f"revogado:{chave}")
        if valor_redis is not None:
            return max(float(valor_redis), valor_local or 0)
        return valor_local
    except Exception:
        logger.exception("Falha ao consultar a revogação de '%s' no Redis — a decidir só com o cache local.", chave)
        return valor_local


async def esta_revogado(tenant_id, usuario_id, jti: str | None, emitido_em: float) -> bool:
    """True se o token devia ser considerado inválido: emitido antes de
    uma revogação de tenant/utilizador, ou o próprio jti foi revogado
    (logout). `emitido_em` é a claim "iat" do JWT (timestamp Unix)."""
    if jti:
        if jti in _jtis_revogados:
            return True
        if _redis_cliente is not None:
            try:
                if await _redis_cliente.exists(f"revogado:jti:{jti}"):
                    return True
            except Exception:
                logger.exception("Falha ao consultar a revogação do jti no Redis — a assumir não revogado desta vez.")

    revogado_tenant_em = await _revogado_desde(f"tenant:{tenant_id}", _revogados_tenant)
    if revogado_tenant_em is not None and revogado_tenant_em > emitido_em:
        return True

    revogado_usuario_em = await _revogado_desde(f"usuario:{usuario_id}", _revogados_usuario)
    if revogado_usuario_em is not None and revogado_usuario_em > emitido_em:
        return True

    return False
