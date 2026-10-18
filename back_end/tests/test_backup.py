"""Backup diário (ver app/core/backup.py) — testado sem pg_dump real
nem storage real: o subprocesso e o storage.py são substituídos por
duplos de teste, o mesmo raciocínio de tests/test_recaptcha.py (não há
biblioteca de mock instalada neste projeto, nem faz sentido exigir um
Postgres/S3 reais só para testar a orquestração)."""
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import backup, cifra_backup


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


# ==========================================
# Cifra dos backups (auditoria de segurança, bloco 4)
# ==========================================
@pytest.fixture(scope="module")
def par_de_chaves():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    return privada, privada.public_key()


def _pem_publico(chave_publica) -> str:
    return chave_publica.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def test_cifra_e_decifra_em_varios_blocos(par_de_chaves, monkeypatch):
    privada, publica = par_de_chaves
    monkeypatch.setattr(cifra_backup, "_TAMANHO_BLOCO", 1000)
    dump = bytes(range(256)) * 20  # 5120 bytes → 6 blocos

    cifrado = cifra_backup.cifrar(dump, publica)

    assert cifrado.startswith(cifra_backup.MAGIC)
    assert dump[:200] not in cifrado
    assert cifra_backup.decifrar(cifrado, privada) == dump


def test_backup_vazio_tambem_e_cifrado(par_de_chaves):
    privada, publica = par_de_chaves
    assert cifra_backup.decifrar(cifra_backup.cifrar(b"", publica), privada) == b""


@pytest.mark.parametrize("estragar", [
    lambda dados: dados[:-1] + bytes([dados[-1] ^ 1]),   # um bit alterado
    lambda dados: dados[:-50],                            # truncado
    lambda dados: b"PGDMP" + dados[5:],                   # cabeçalho trocado
])
def test_backup_alterado_ou_truncado_e_recusado(par_de_chaves, estragar):
    privada, publica = par_de_chaves
    cifrado = cifra_backup.cifrar(b"dados da base" * 100, publica)
    with pytest.raises(cifra_backup.BackupInvalido):
        cifra_backup.decifrar(estragar(cifrado), privada)


def test_bloco_final_removido_e_detetado(par_de_chaves, monkeypatch):
    """Cortar o ficheiro exatamente no fim de um bloco não pode passar por
    um backup completo mais pequeno."""
    privada, publica = par_de_chaves
    monkeypatch.setattr(cifra_backup, "_TAMANHO_BLOCO", 100)
    cifrado = cifra_backup.cifrar(b"x" * 250, publica)  # blocos de 100, 100, 50
    ultimo_bloco = 4 + 50 + 16  # tamanho + dados + tag GCM
    with pytest.raises(cifra_backup.BackupInvalido):
        cifra_backup.decifrar(cifrado[:-ultimo_bloco], privada)


def test_chave_privada_errada_e_recusada(par_de_chaves):
    _, publica = par_de_chaves
    outra = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    with pytest.raises(cifra_backup.BackupInvalido):
        cifra_backup.decifrar(cifra_backup.cifrar(b"segredo", publica), outra)


def test_chave_publica_fraca_e_recusada():
    fraca = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    with pytest.raises(ValueError):
        cifra_backup.carregar_chave_publica(_pem_publico(fraca))


def test_par_gerado_pelo_script_funciona_com_frase_passe(tmp_path):
    pem_privado, pem_publico = cifra_backup.gerar_par_de_chaves("frase-passe-de-teste")
    assert b"ENCRYPTED" in pem_privado
    (tmp_path / "privada.pem").write_bytes(pem_privado)
    (tmp_path / "publica.pem").write_bytes(pem_publico)

    publica = cifra_backup.carregar_chave_publica(str(tmp_path / "publica.pem"))
    privada = cifra_backup.carregar_chave_privada(str(tmp_path / "privada.pem"), "frase-passe-de-teste")
    assert cifra_backup.decifrar(cifra_backup.cifrar(b"ok", publica), privada) == b"ok"
    with pytest.raises(ValueError):
        cifra_backup.carregar_chave_privada(str(tmp_path / "privada.pem"), "frase-errada")


async def test_backup_diario_sai_cifrado_com_a_chave_publica(par_de_chaves, monkeypatch):
    privada, publica = par_de_chaves
    guardados = {}

    async def _dump_falso():
        return b"PGDMP conteudo real do dump"

    async def _guardar_falso(chave, conteudo, content_type):
        guardados[chave] = conteudo

    async def _retencao_falsa():
        return 0

    monkeypatch.setattr(backup, "BACKUP_CHAVE_PUBLICA", _pem_publico(publica))
    monkeypatch.setattr(backup, "_correr_pg_dump", _dump_falso)
    monkeypatch.setattr(backup.storage, "guardar_ficheiro", _guardar_falso)
    monkeypatch.setattr(backup, "_aplicar_retencao", _retencao_falsa)

    resultado = await backup.executar_backup_diario()

    assert resultado["cifrado"] is True and resultado["chave"].endswith(".dump.enc")
    conteudo = guardados[resultado["chave"]]
    assert b"PGDMP" not in conteudo
    assert cifra_backup.decifrar(conteudo, privada) == b"PGDMP conteudo real do dump"


async def test_com_bucket_proprio_a_app_nunca_apaga_backups(monkeypatch):
    """Com BACKUP_S3_BUCKET, a retenção é da regra de ciclo de vida do
    bucket — as credenciais do servidor podem ser só de escrita."""
    async def _nao_devia_listar(prefixo):
        raise AssertionError("não devia listar o bucket")

    monkeypatch.setattr(backup, "_s3_backups", object())
    monkeypatch.setattr(backup.storage, "listar_ficheiros", _nao_devia_listar)
    assert await backup._aplicar_retencao() == 0


def test_retencao_reconhece_backups_cifrados():
    quando = datetime(2026, 9, 20, 3, 0, 0, tzinfo=timezone.utc)
    assert backup._REGEX_NOME.search(backup._chave_do_backup(quando, cifrado=True))
