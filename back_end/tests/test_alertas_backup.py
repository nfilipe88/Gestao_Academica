"""Um backup que falha (ou que nem chega a correr) tem de se fazer notar: quem
só olha para o log descobre no dia em que precisa dele. Ver app/core/scheduler.py."""
import httpx

from app.core import backup, fila_notificacoes, scheduler
from tests.test_planos_por_aluno_modulo import _criar_super_admin


def _preparar(monkeypatch) -> list[dict]:
    enviados: list[dict] = []

    async def _agendar_falso(_funcao_envio, **kwargs):
        enviados.append(kwargs)

    async def _lock_livre(*_args, **_kwargs):
        return True

    monkeypatch.setattr(fila_notificacoes, "agendar_email", _agendar_falso)
    monkeypatch.setattr(scheduler, "tentar_obter_lock", _lock_livre)
    return enviados


async def test_falha_do_backup_avisa_o_super_admin(client, monkeypatch):
    enviados = _preparar(monkeypatch)
    await _criar_super_admin(client)

    async def _falha():
        raise RuntimeError("pg_dump morreu")

    monkeypatch.setattr(backup, "executar_backup_diario", _falha)
    assert await scheduler.job_backup_diario() == {}

    avisos = [e for e in enviados if e["assunto"] == "Falha no backup diário"]
    assert any(e["destinatario"].startswith("superadmin.teste.") for e in avisos)
    assert "pg_dump morreu" in avisos[0]["corpo_html"]


async def test_backup_bem_sucedido_avisa_a_monitorizacao(monkeypatch):
    enviados = _preparar(monkeypatch)
    pedidos: list[str] = []

    async def _sucesso():
        return {"chave": "_backups/x.dump.enc"}

    async def _get_falso(_cliente, url, **_kwargs):
        pedidos.append(url)
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(backup, "executar_backup_diario", _sucesso)
    monkeypatch.setattr(httpx.AsyncClient, "get", _get_falso)
    monkeypatch.setenv("BACKUP_HEARTBEAT_URL", "https://monitorizacao.exemplo/ping/abc")

    assert await scheduler.job_backup_diario() == {"chave": "_backups/x.dump.enc"}
    assert pedidos == ["https://monitorizacao.exemplo/ping/abc"]
    assert enviados == []


async def test_falha_na_monitorizacao_nao_estraga_o_backup(monkeypatch):
    _preparar(monkeypatch)

    async def _sucesso():
        return {"chave": "_backups/x.dump.enc"}

    async def _get_falha(_cliente, url, **_kwargs):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(backup, "executar_backup_diario", _sucesso)
    monkeypatch.setattr(httpx.AsyncClient, "get", _get_falha)
    monkeypatch.setenv("BACKUP_HEARTBEAT_URL", "https://monitorizacao.exemplo/ping/abc")

    assert await scheduler.job_backup_diario() == {"chave": "_backups/x.dump.enc"}
