"""
Eventos de segurança: regista tentativas de acesso indevido (com IP,
browser e, se houver sessão, utilizador e escola), avisa quem tem de
saber e bloqueia temporariamente um IP que insiste.

Quem regista o quê:
  - MonitorSegurancaMiddleware (abaixo): endereços de sondagem/ataque
    (/.env, wp-admin, ../, <script>, union select) e pedidos de IPs
    bloqueados;
  - app/core/security.py: token forjado; perfil sem acesso à área;
  - app/core/validacao_ficheiros.py e cruds/importacao.py: ficheiros
    maliciosos;
  - api/v1/auth.py, cruds/dois_fatores.py, core/recaptcha.py: força bruta.

Duas regras para não tratar o normal como ataque:
  - um token EXPIRADO não é registado (acontece a cada ~20 min a toda a
    gente); só um token com assinatura inválida (forjado);
  - só eventos ANÓNIMOS (sem sessão) contam para o bloqueio automático de
    IP — numa escola, muitas pessoas partilham o mesmo IP público; um
    utilizador identificado que tenta onde não deve vai para o registo e
    para o Gestor, mas nunca bloqueia a rede da escola inteira.

Nunca levanta exceções: uma falha a registar nunca pode estragar o pedido
em si (mesmo princípio de fila_notificacoes/auditoria).
"""
import contextvars
import json
import logging
import os
import re
import time
import uuid
from urllib.parse import unquote, unquote_plus

from sqlalchemy import select

logger = logging.getLogger("seguranca")

# ---- Tipos e gravidades ----
TOKEN_FORJADO = "TOKEN_FORJADO"
ACESSO_NEGADO = "ACESSO_NEGADO"
FICHEIRO_MALICIOSO = "FICHEIRO_MALICIOSO"
FICHEIRO_RECUSADO = "FICHEIRO_RECUSADO"
SONDAGEM = "SONDAGEM"
LOGIN_FALHADO = "LOGIN_FALHADO"
FORCA_BRUTA = "FORCA_BRUTA"
DOIS_FATORES_FALHADO = "DOIS_FATORES_FALHADO"
RECAPTCHA_FALHADO = "RECAPTCHA_FALHADO"
IP_BLOQUEADO = "IP_BLOQUEADO"

BAIXA, MEDIA, ALTA = "BAIXA", "MEDIA", "ALTA"
_PONTOS = {BAIXA: 1, MEDIA: 3, ALTA: 10}

# ---- Bloqueio automático de IP ----
LIMITE_PONTOS = int(os.getenv("SEGURANCA_LIMITE_PONTOS", "30"))
JANELA_SEGUNDOS = int(os.getenv("SEGURANCA_JANELA_SEGUNDOS", "600"))
BLOQUEIO_SEGUNDOS = int(os.getenv("SEGURANCA_BLOQUEIO_SEGUNDOS", "3600"))
# IPs que nunca são bloqueados (ex.: o escritório de quem administra a
# plataforma), separados por vírgulas.
IPS_NUNCA_BLOQUEAR = {ip.strip() for ip in os.getenv("SEGURANCA_IPS_NUNCA_BLOQUEAR", "").split(",") if ip.strip()}

# Avisos por e-mail: no máximo um por (destino, IP/utilizador, tipo) nesta janela.
_ALERTA_SUPER_ADMIN_SEGUNDOS = 900
_ALERTA_GESTOR_SEGUNDOS = 3600

# ---- Contexto do pedido (preenchido pelo middleware e por security.py) ----
_contexto: contextvars.ContextVar[dict | None] = contextvars.ContextVar("contexto_seguranca", default=None)


def definir_utilizador(usuario_id, tenant_id) -> None:
    ctx = _contexto.get()
    if ctx is not None:
        ctx["usuario_id"] = usuario_id
        ctx["tenant_id"] = tenant_id


# ---- Armazenamento de pontos/bloqueios/avisos: Redis entre instâncias, memória como recurso ----
REDIS_URL = os.getenv("REDIS_URL")
_redis = None
if REDIS_URL:
    import redis.asyncio as redis_asyncio
    _redis = redis_asyncio.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)

_mem_pontos: dict[str, tuple[int, float]] = {}
_mem_bloqueios: dict[str, tuple[float, str]] = {}
_mem_reservas: dict[str, float] = {}


def limpar_memoria() -> None:
    """Para os testes: cada teste começa sem pontos nem bloqueios."""
    _mem_pontos.clear()
    _mem_bloqueios.clear()
    _mem_reservas.clear()


async def _somar_pontos(ip: str, pontos: int) -> int:
    if _redis is not None:
        try:
            chave = f"seguranca:pontos:{ip}"
            total = await _redis.incrby(chave, pontos)
            if total == pontos:
                await _redis.expire(chave, JANELA_SEGUNDOS)
            return int(total)
        except Exception:
            logger.exception("Redis indisponível nos eventos de segurança — a contar em memória local.")
    agora = time.monotonic()
    total, expira = _mem_pontos.get(ip, (0, 0.0))
    if expira < agora:
        total, expira = 0, agora + JANELA_SEGUNDOS
    total += pontos
    _mem_pontos[ip] = (total, expira)
    return total


async def _reservar(chave: str, segundos: int) -> bool:
    """True só da primeira vez nesta janela — evita uma enxurrada de e-mails iguais."""
    if _redis is not None:
        try:
            return bool(await _redis.set(f"seguranca:aviso:{chave}", "1", nx=True, ex=segundos))
        except Exception:
            logger.exception("Redis indisponível nos avisos de segurança — a decidir em memória local.")
    agora = time.monotonic()
    if _mem_reservas.get(chave, 0.0) > agora:
        return False
    _mem_reservas[chave] = agora + segundos
    return True


async def ip_bloqueado(ip: str) -> bool:
    if _redis is not None:
        try:
            return bool(await _redis.exists(f"seguranca:bloqueio:{ip}"))
        except Exception:
            logger.exception("Redis indisponível a consultar bloqueios — a decidir em memória local.")
    ate = _mem_bloqueios.get(ip)
    return bool(ate and ate[0] > time.time())


async def bloquear_ip(ip: str, motivo: str) -> None:
    ate = time.time() + BLOQUEIO_SEGUNDOS
    _mem_bloqueios[ip] = (ate, motivo)
    if _redis is not None:
        try:
            await _redis.set(f"seguranca:bloqueio:{ip}", json.dumps({"ate": ate, "motivo": motivo}), ex=BLOQUEIO_SEGUNDOS)
        except Exception:
            logger.exception("Redis indisponível a gravar o bloqueio de %s — fica só nesta instância.", ip)


async def listar_bloqueios() -> list[dict]:
    agora = time.time()
    bloqueios: dict[str, dict] = {
        ip: {"ip": ip, "ate": ate, "motivo": motivo} for ip, (ate, motivo) in _mem_bloqueios.items() if ate > agora
    }
    if _redis is not None:
        try:
            async for chave in _redis.scan_iter("seguranca:bloqueio:*"):
                valor = await _redis.get(chave)
                if valor:
                    dados = json.loads(valor)
                    ip = chave.removeprefix("seguranca:bloqueio:")
                    bloqueios[ip] = {"ip": ip, "ate": dados["ate"], "motivo": dados["motivo"]}
        except Exception:
            logger.exception("Redis indisponível a listar bloqueios.")
    return sorted(bloqueios.values(), key=lambda b: b["ate"], reverse=True)


async def desbloquear_ip(ip: str) -> None:
    _mem_bloqueios.pop(ip, None)
    _mem_pontos.pop(ip, None)
    if _redis is not None:
        try:
            await _redis.delete(f"seguranca:bloqueio:{ip}", f"seguranca:pontos:{ip}")
        except Exception:
            logger.exception("Redis indisponível a desbloquear %s.", ip)


# ---- Registo ----
async def registar(
    tipo: str, gravidade: str, detalhe: str | None = None, *,
    email: str | None = None, usuario_id=None, tenant_id=None, ip: str | None = None,
) -> None:
    try:
        await _registar(tipo, gravidade, detalhe, email=email, usuario_id=usuario_id, tenant_id=tenant_id, ip=ip)
    except Exception:
        logger.exception("Falha a registar o evento de segurança %s.", tipo)


async def _registar(tipo, gravidade, detalhe, *, email, usuario_id, tenant_id, ip) -> None:
    from app.database.session import AsyncSessionLocalSistema
    from app.database.models import Usuario
    from app.database.models_usuarios import EventoSeguranca

    ctx = _contexto.get() or {}
    ip = ip or ctx.get("ip") or "desconhecido"
    usuario_id = usuario_id or ctx.get("usuario_id")
    tenant_id = tenant_id or ctx.get("tenant_id")

    async with AsyncSessionLocalSistema() as db:
        if usuario_id and not email:
            email = (await db.execute(select(Usuario.email).where(Usuario.id == usuario_id))).scalar_one_or_none()
        evento = EventoSeguranca(
            id=uuid.uuid4(), tipo=tipo, gravidade=gravidade, ip=ip[:45],
            user_agent=(ctx.get("user_agent") or "")[:255] or None,
            tenant_id=tenant_id, usuario_id=usuario_id, email=(email or None) and email[:255],
            metodo=ctx.get("metodo"), caminho=(ctx.get("caminho") or "")[:500] or None,
            detalhe=detalhe,
        )
        db.add(evento)
        await db.commit()

    logger.warning(
        "Evento de segurança %s (%s) de %s%s: %s %s — %s",
        tipo, gravidade, ip, f" [{email}]" if email else "", ctx.get("metodo") or "", ctx.get("caminho") or "", detalhe or "",
    )

    if gravidade == ALTA:
        await _avisar_super_admins(evento)
    if tenant_id and gravidade in (MEDIA, ALTA):
        await _avisar_gestores(evento)

    # Só o anónimo conta para bloquear o IP (ver docstring do módulo).
    if usuario_id is None and ip not in IPS_NUNCA_BLOQUEAR and ip != "desconhecido":
        total = await _somar_pontos(ip, _PONTOS.get(gravidade, 1))
        if total >= LIMITE_PONTOS and not await ip_bloqueado(ip):
            motivo = f"{total} pontos de eventos suspeitos em {JANELA_SEGUNDOS // 60} min (último: {tipo})"
            await bloquear_ip(ip, motivo)
            await registar(IP_BLOQUEADO, ALTA, f"Bloqueado por {BLOQUEIO_SEGUNDOS // 60} min: {motivo}.", ip=ip)


def _linhas_evento(evento) -> str:
    from app.core.email import escapar
    linhas = [
        ("Tipo", evento.tipo), ("Gravidade", evento.gravidade), ("Endereço IP", evento.ip),
        ("Utilizador", evento.email or "— (sem sessão)"),
        ("Pedido", f"{evento.metodo or ''} {evento.caminho or ''}".strip() or "—"),
        ("Browser", evento.user_agent or "—"), ("Detalhe", evento.detalhe or "—"),
    ]
    return "".join(f"<tr><td style='padding:4px 12px 4px 0;color:#64748b'>{r}</td><td>{escapar(v)}</td></tr>" for r, v in linhas)


async def _enviar_aviso(destinatarios: list[str], titulo: str, introducao: str, evento) -> None:
    from app.core import fila_notificacoes
    from app.core.email import enviar_email, template_base
    corpo = template_base(titulo, f"<p>{introducao}</p><table>{_linhas_evento(evento)}</table>")
    for destino in destinatarios:
        await fila_notificacoes.agendar_email(enviar_email, destinatario=destino, assunto=titulo, corpo_html=corpo)


async def _avisar_super_admins(evento) -> None:
    if not await _reservar(f"sa:{evento.ip}:{evento.tipo}", _ALERTA_SUPER_ADMIN_SEGUNDOS):
        return
    from app.database.session import AsyncSessionLocalSistema
    from app.database.models import Usuario
    async with AsyncSessionLocalSistema() as db:
        emails = (await db.execute(
            # Super Admin e Suporte: é o Suporte quem ajuda a desbloquear quem foi bloqueado por engano.
            select(Usuario.email).where(Usuario.perfil_acesso.in_(("SUPER_ADMIN", "SUPORTE")), Usuario.ativo.is_(True))
        )).scalars().all()
    await _enviar_aviso(
        list(emails), f"Alerta de segurança: {evento.tipo}",
        "A plataforma detetou uma tentativa de acesso indevido. Detalhes no painel de Segurança:", evento,
    )


async def _avisar_gestores(evento) -> None:
    quem = evento.usuario_id or evento.ip
    if not await _reservar(f"gestor:{evento.tenant_id}:{quem}:{evento.tipo}", _ALERTA_GESTOR_SEGUNDOS):
        return
    from app.database.session import AsyncSessionLocalSistema
    from app.database.models import Usuario
    async with AsyncSessionLocalSistema() as db:
        emails = (await db.execute(
            select(Usuario.email).where(
                Usuario.tenant_id == evento.tenant_id, Usuario.perfil_acesso == "GESTOR", Usuario.ativo.is_(True)
            )
        )).scalars().all()
    await _enviar_aviso(
        list(emails), "Alerta de segurança na sua escola",
        "Foi detetada uma tentativa de acesso indevido na sua escola. Detalhes em Gestão de Acessos → Segurança:", evento,
    )


# ---- Deteção de endereços de sondagem/ataque ----
# Padrões de ferramentas de varrimento e de ataques conhecidos. Específicos
# de propósito: uma pesquisa normal por "select" ou "union" não dispara.
_PADROES_ALTA = re.compile(
    r"(\.\./|\.\.\\|/etc/passwd|/proc/self|<script|javascript:|union(\s|\+|/\*.*\*/)+select|'\s*or\s*'?1'?\s*=\s*'?1"
    r"|;\s*(drop|delete|insert|update)\s|sleep\(\d|benchmark\(|\$\{jndi:)",
    re.IGNORECASE,
)
_PADROES_SONDAGEM = re.compile(
    r"(/\.env|/\.git|/\.svn|/\.aws|/\.ssh|/\.htaccess|wp-admin|wp-login|wp-content|xmlrpc\.php|phpmyadmin|/pma/"
    r"|\.php(\?|$)|\.asp(x)?(\?|$)|\.jsp(\?|$)|cgi-bin|/actuator|/server-status|/config\.json|/boaform|/HNAP1"
    r"|/vendor/phpunit|/console/|/solr/|/manager/html)",
    re.IGNORECASE,
)


def classificar_endereco(caminho: str, query: str) -> tuple[str, str] | None:
    """(gravidade, motivo) se o endereço parecer sondagem/ataque, senão None."""
    # Duas passagens: apanha também a codificação dupla (%252e%252e = ../).
    # Na query, "+" é um espaço ("1'+or+'1'='1").
    alvo = unquote(unquote(caminho)) + ("?" + unquote_plus(unquote_plus(query)) if query else "")
    if _PADROES_ALTA.search(alvo):
        return ALTA, "Padrão de ataque no endereço (path traversal, injeção de SQL/script)"
    if _PADROES_SONDAGEM.search(alvo):
        return MEDIA, "Endereço típico de ferramentas de varrimento (ficheiros de configuração, painéis de outros sistemas)"
    return None


class MonitorSegurancaMiddleware:
    """ASGI puro (mesma razão de cabecalhos.py): recusa IPs bloqueados,
    deteta endereços de sondagem/ataque e guarda o contexto do pedido
    (IP, browser, endereço) para os registos feitos mais à frente."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cliente = scope.get("client")
        ip = cliente[0] if cliente else "desconhecido"
        cabecalhos = dict(scope.get("headers") or [])
        caminho = scope.get("path", "")
        query = (scope.get("query_string") or b"").decode("latin-1")
        token = _contexto.set({
            "ip": ip,
            "user_agent": cabecalhos.get(b"user-agent", b"").decode("latin-1", "replace"),
            "metodo": scope.get("method"),
            "caminho": f"{caminho}?{query}" if query else caminho,
            "usuario_id": None, "tenant_id": None,
        })
        try:
            if caminho != "/api/v1/health" and await ip_bloqueado(ip):
                await _responder(send, 403, "O seu endereço foi bloqueado temporariamente por atividade suspeita. Tente mais tarde.")
                return

            suspeito = classificar_endereco(caminho, query)
            if suspeito:
                gravidade, motivo = suspeito
                await registar(SONDAGEM, gravidade, motivo)
                await _responder(send, 404, "Not Found")
                return

            await self.app(scope, receive, send)
        finally:
            _contexto.reset(token)


async def _responder(send, estado: int, detalhe: str) -> None:
    corpo = json.dumps({"detail": detalhe}).encode()
    await send({
        "type": "http.response.start", "status": estado,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(corpo)).encode())],
    })
    await send({"type": "http.response.body", "body": corpo})
