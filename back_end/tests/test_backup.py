"""Backup diário (ver app/core/backup.py) — testado sem pg_dump real
nem storage real: o subprocesso e o storage.py são substituídos por
duplos de teste, o mesmo raciocínio de tests/test_recaptcha.py (não há
biblioteca de mock instalada neste projeto, nem faz sentido exigir um
Postgres/S3 reais só para testar a orquestração)."""
from datetime import datetime, timedelta, timezone

from app.core import backup


def test_dsn_para_pg_dump_remove_sufixo_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_MIGRACOES", "postgresql+asyncpg://postgres:senha@localhost:5432/academic_db")
    assert backup._dsn_para_pg_dump() == "postgresql://postgres:senha@localhost:5432/academic_db"


def test_dsn_para_pg_dump_sem_env_levanta_erro(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_MIGRACOES", raising=False)
    try:
        backup._dsn_para_pg_dump()
        assert False, "devia ter levantado RuntimeError"
    except RuntimeError:
        pass


def test_chave_do_backup_segue_o_padrao_esperado():
    quando = datetime(2026, 9, 20, 3, 0, 0, tzinfo=timezone.utc)
    assert backup._chave_do_backup(quando) == "_backups/academic_db_20260920_030000.dump"


async def test_executar_backup_diario_orquestra_dump_upload_e_retencao(monkeypatch):
    """Não corre pg_dump nem toca no storage real — só confirma que
    executar_backup_diario liga as três peças (dump → upload →
    retenção) pela ordem certa e devolve o resumo esperado."""
    chamadas = []

    async def _dump_falso():
        chamadas.append("dump")
        return b"conteudo-fake-do-dump"

    async def _guardar_falso(chave, conteudo, content_type):
        chamadas.append(("guardar", chave, conteudo, content_type))

    async def _retencao_falsa():
        chamadas.append("retencao")
        return 2

    monkeypatch.setattr(backup, "_correr_pg_dump", _dump_falso)
    monkeypatch.setattr(backup.storage, "guardar_ficheiro", _guardar_falso)
    monkeypatch.setattr(backup, "_aplicar_retencao", _retencao_falsa)

    resultado = await backup.executar_backup_diario()

    assert [c if isinstance(c, str) else c[0] for c in chamadas] == ["dump", "guardar", "retencao"]
    assert resultado["tamanho_bytes"] == len(b"conteudo-fake-do-dump")
    assert resultado["apagados_pela_retencao"] == 2
    assert resultado["chave"].startswith("_backups/academic_db_") and resultado["chave"].endswith(".dump")


async def test_aplicar_retencao_apaga_so_os_backups_antigos(monkeypatch):
    agora = datetime.now(timezone.utc)
    antigo = agora - timedelta(days=backup.BACKUP_RETENCAO_DIAS + 1)
    recente = agora - timedelta(days=1)

    chave_antiga = backup._chave_do_backup(antigo)
    chave_recente = backup._chave_do_backup(recente)
    chave_invalida = "_backups/ficheiro-fora-do-padrao.txt"

    async def _listar_falso(prefixo):
        return [chave_antiga, chave_recente, chave_invalida]

    apagadas = []

    async def _apagar_falso(chave):
        apagadas.append(chave)

    monkeypatch.setattr(backup.storage, "listar_ficheiros", _listar_falso)
    monkeypatch.setattr(backup.storage, "apagar_ficheiro", _apagar_falso)

    total = await backup._aplicar_retencao()

    assert total == 1
    assert apagadas == [chave_antiga]
