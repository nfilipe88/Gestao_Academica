"""
Trilha de auditoria GERAL — regista automaticamente quem criou,
alterou ou apagou qualquer linha em qualquer tabela do sistema, sem
precisar de uma chamada manual em cada crud (ao contrário de
UsuarioAuditoria/RegistroNotaAuditoria, escritas à mão nos dois sítios
onde já existiam).

Como funciona: um listener `before_flush` do SQLAlchemy corre em TODA
sessão (Session/AsyncSession, tenant e admin) mesmo antes de o
INSERT/UPDATE/DELETE ser emitido, inspeciona session.new/dirty/deleted
e cria um AuditLog para cada alteração real. "Quem" vem de uma
contextvar (`_ator_atual`) definida logo no início do pedido em
app/database/session.py — funciona em código assíncrono porque o
`greenlet_spawn` que o SQLAlchemy async usa para correr o flush
propaga o contextvars.Context corrente (ver sqlalchemy/util/_concurrency_py3k.py),
e cada pedido HTTP corre na sua própria Task do asyncio, por isso o
ator de um pedido nunca escapa para outro em concorrência.
"""
import contextvars
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

from app.database.models_auditoria import AuditLog

_ator_atual: contextvars.ContextVar[dict | None] = contextvars.ContextVar("auditoria_ator_atual", default=None)


def definir_ator_auditoria(usuario_id, tenant_id, perfil_acesso: str | None) -> None:
    """Chamado no início de cada pedido autenticado (ver session.py) — nunca diretamente por um crud."""
    _ator_atual.set({"usuario_id": usuario_id, "tenant_id": tenant_id, "perfil_acesso": perfil_acesso})


# Tabelas fora do âmbito desta auditoria geral: já são elas próprias
# registos de histórico (auditar um log duplicaria a informação para
# sempre), ou são artefactos técnicos sem valor de "ação humana" —
# tokens, filas, e o próprio audit_log.
_TABELAS_EXCLUIDAS = {
    "audit_log", "usuario_auditoria", "registro_nota_auditoria",
    "login_historico", "refresh_token", "password_reset_token",
    "notificacao", "ticket_suporte", "ticket_mensagem",
}

# Nunca gravar segredos em claro num campo de auditoria, mesmo que o
# valor em si já esteja em hash — não há necessidade de o expor aqui.
_COLUNAS_SENSIVEIS = {"palavra_passe_hash", "senha_hash", "hash_senha", "token", "refresh_token_hash"}


def _serializar(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, uuid.UUID):
        return str(valor)
    return valor


def _tabela_de(obj) -> str | None:
    tabela = getattr(obj.__class__, "__tablename__", None)
    if tabela is None or tabela in _TABELAS_EXCLUIDAS or isinstance(obj, AuditLog):
        return None
    return tabela


def _pk_de(obj) -> str:
    insp = inspect(obj)
    return "|".join(str(getattr(obj, coluna.name)) for coluna in insp.mapper.primary_key)


def _snapshot(obj) -> dict:
    insp = inspect(obj)
    return {
        c.key: _serializar(getattr(obj, c.key))
        for c in insp.mapper.column_attrs
        if c.key not in _COLUNAS_SENSIVEIS
    }


def _tenant_id_de(obj, ator: dict | None):
    return getattr(obj, "tenant_id", None) or (ator["tenant_id"] if ator else None)


def _criar_registo(obj, acao: str, alteracoes: dict, ator: dict | None) -> AuditLog:
    return AuditLog(
        tenant_id=_tenant_id_de(obj, ator),
        autor_id=ator["usuario_id"] if ator else None,
        autor_perfil=ator["perfil_acesso"] if ator else None,
        acao=acao, entidade=_tabela_de(obj), entidade_id=_pk_de(obj),
        alteracoes=alteracoes,
    )


@event.listens_for(Session, "before_flush")
def _registar_auditoria(session, flush_context, instances):
    ator = _ator_atual.get()
    novos_logs = []

    for obj in list(session.new):
        if _tabela_de(obj) is None:
            continue
        novos_logs.append(_criar_registo(obj, "CRIADO", _snapshot(obj), ator))

    for obj in list(session.dirty):
        if _tabela_de(obj) is None or not session.is_modified(obj, include_collections=False):
            continue
        insp = inspect(obj)
        alteracoes = {}
        for c in insp.mapper.column_attrs:
            if c.key in _COLUNAS_SENSIVEIS:
                continue
            hist = get_history(obj, c.key)
            if not hist.has_changes():
                continue
            alteracoes[c.key] = {
                "antes": _serializar(hist.deleted[0]) if hist.deleted else None,
                "depois": _serializar(hist.added[0]) if hist.added else _serializar(getattr(obj, c.key)),
            }
        if alteracoes:
            novos_logs.append(_criar_registo(obj, "ALTERADO", alteracoes, ator))

    for obj in list(session.deleted):
        if _tabela_de(obj) is None:
            continue
        novos_logs.append(_criar_registo(obj, "APAGADO", _snapshot(obj), ator))

    for log in novos_logs:
        session.add(log)
