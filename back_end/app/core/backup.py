"""Backup diário da base de dados (pg_dump) para armazenamento externo
ao servidor da base de dados (ver app/core/storage.py — o mesmo
S3-compatível já usado para logótipos/anexos). Corre automaticamente
via app/core/scheduler.py; scripts/backup_manual.py dispara-o na hora
para testar a configuração sem esperar pelo relógio.

pg_dump em vez de um export à mão a partir do SQLAlchemy: é a
ferramenta oficial do Postgres, cobre tudo (schema, dados, sequences,
policies de RLS) sem ter de manter uma lista própria de tabelas — o
mesmo raciocínio de "reaproveitar o motor certo" já seguido no resto
do projeto (Alembic para migrações, xhtml2pdf para PDFs).

Formato -Fc (custom, já comprimido): ao contrário de um .sql em texto,
permite restauro seletivo e paralelo com pg_restore — não é usado hoje,
mas fica disponível sem custo extra (ver scripts/restaurar_db.py).

Um backup que vive só no disco do próprio servidor da base de dados não
protege contra a perda desse servidor — por isso isto usa sempre
app/core/storage.py, cujo aviso já existente (log no arranque) sobre
S3_BUCKET não configurado se aplica aqui com ainda mais peso: sem S3
real, os backups ficam tão vulneráveis quanto a base de dados que
supostamente protegem.

Em produção, cada backup sai cifrado com a chave pública de backup
(ver app/core/cifra_backup.py) para um bucket próprio (BACKUP_S3_*),
separado do da aplicação.
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone

from app.core import cifra_backup, storage

logger = logging.getLogger("backup")

# Cifra (ver app/core/cifra_backup.py): caminho para o ficheiro .pem da
# chave pública, ou o próprio PEM numa só linha. Sem ela, os
# backups ficam em claro — só aceitável em desenvolvimento
# (scripts/verificar_env_producao.py trata-o como bloqueador).
BACKUP_CHAVE_PUBLICA = os.getenv("BACKUP_CHAVE_PUBLICA")

# Bucket próprio para os backups, com credenciais próprias — separado do
# dos ficheiros da aplicação (S3_*): quem obtiver as credenciais da app
# não lê nem apaga os backups. Recomendado: credenciais só de escrita
# (PutObject) e a retenção feita por uma regra de ciclo de vida do
# próprio bucket — por isso, com bucket próprio, a app nunca lista nem
# apaga backups (ver _aplicar_retencao). Sem BACKUP_S3_BUCKET, cai para o
# storage da aplicação (desenvolvimento).
BACKUP_S3_BUCKET = os.getenv("BACKUP_S3_BUCKET")
BACKUP_S3_ENDPOINT_URL = os.getenv("BACKUP_S3_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL") or None
BACKUP_S3_REGION = os.getenv("BACKUP_S3_REGION") or os.getenv("S3_REGION", "us-east-1")

_s3_backups = None
if BACKUP_S3_BUCKET:
    import boto3
    _s3_backups = boto3.client(
        "s3", endpoint_url=BACKUP_S3_ENDPOINT_URL, region_name=BACKUP_S3_REGION,
        aws_access_key_id=os.getenv("BACKUP_S3_ACCESS_KEY"), aws_secret_access_key=os.getenv("BACKUP_S3_SECRET_KEY"),
    )

if not BACKUP_CHAVE_PUBLICA:
    logger.warning(
        "BACKUP_CHAVE_PUBLICA não definida — os backups da base de dados ficam SEM cifra. "
        "Só aceitável em desenvolvimento; ver scripts/gerar_chaves_backup.py."
    )

# Só precisa de apontar para o executável quando pg_dump não está no
# PATH — normal numa instalação Windows do Postgres (ver .env.example);
# em Docker/Linux com o cliente Postgres instalado, "pg_dump" já resolve.
PG_DUMP_PATH = os.getenv("PG_DUMP_PATH", "pg_dump")

# Quantos dias de backups diários manter no storage antes de apagar os
# mais antigos — sem isto, o bucket cresce para sempre com mais um
# ficheiro por dia.
BACKUP_RETENCAO_DIAS = int(os.getenv("BACKUP_RETENCAO_DIAS", "14"))

_PREFIXO_CHAVE = "_backups/"
_REGEX_NOME = re.compile(r"academic_db_(\d{8})_(\d{6})\.dump(\.enc)?$")


def _dsn_para_pg_dump() -> str:
    """DATABASE_URL_MIGRACOES já é a ligação com privilégios suficientes
    (role postgres, superuser — ver .env.example) e pg_dump aceita uma
    connection string estilo libpq diretamente, só sem o sufixo
    "+asyncpg" (esse é só para o SQLAlchemy escolher o driver assíncrono)."""
    url = os.getenv("DATABASE_URL_MIGRACOES")
    if not url:
        raise RuntimeError("DATABASE_URL_MIGRACOES não configurada — não é possível fazer backup.")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _correr_pg_dump() -> bytes:
    processo = await asyncio.create_subprocess_exec(
        PG_DUMP_PATH, _dsn_para_pg_dump(), "-Fc",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await processo.communicate()
    if processo.returncode != 0:
        raise RuntimeError(f"pg_dump falhou (código {processo.returncode}): {stderr.decode(errors='replace')}")
    return stdout


def _chave_do_backup(quando: datetime, cifrado: bool = False) -> str:
    return f"{_PREFIXO_CHAVE}academic_db_{quando.strftime('%Y%m%d_%H%M%S')}.dump" + (".enc" if cifrado else "")


async def guardar_backup(chave: str, conteudo: bytes) -> None:
    if _s3_backups is None:
        await storage.guardar_ficheiro(chave, conteudo, "application/octet-stream")
        return
    await asyncio.to_thread(
        _s3_backups.put_object, Bucket=BACKUP_S3_BUCKET, Key=chave, Body=conteudo, ContentType="application/octet-stream"
    )


async def obter_backup(chave: str) -> bytes | None:
    """Usado por scripts/restaurar_db.py — com bucket próprio, quem
    restaura corre o script com credenciais de LEITURA desse bucket (as
    do servidor podem ser só de escrita)."""
    if _s3_backups is None:
        return await storage.obter_ficheiro(chave)

    def _ler():
        try:
            return _s3_backups.get_object(Bucket=BACKUP_S3_BUCKET, Key=chave)["Body"].read()
        except _s3_backups.exceptions.NoSuchKey:
            return None
    return await asyncio.to_thread(_ler)


async def _aplicar_retencao() -> int:
    """Apaga backups com mais de BACKUP_RETENCAO_DIAS. Devolve quantos
    foram apagados. Chaves que não seguem o padrão esperado (ex.: um
    ficheiro colocado à mão na mesma pasta) são ignoradas em vez de
    apagadas — mais vale nunca apagar algo por engano do que ser
    demasiado agressivo na limpeza."""
    if _s3_backups is not None:
        # Bucket próprio: a retenção é da regra de ciclo de vida do bucket
        # (as credenciais do servidor podem nem ter permissão para apagar).
        return 0
    chaves = await storage.listar_ficheiros(_PREFIXO_CHAVE)
    limite = datetime.now(timezone.utc).timestamp() - BACKUP_RETENCAO_DIAS * 86400
    apagados = 0
    for chave in chaves:
        m = _REGEX_NOME.search(chave)
        if not m:
            continue
        quando = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        if quando.timestamp() < limite:
            await storage.apagar_ficheiro(chave)
            apagados += 1
    return apagados


async def executar_backup_diario() -> dict:
    """Chamada pelo job agendado (scheduler.py) e por
    scripts/backup_manual.py para testar/forçar manualmente."""
    inicio = datetime.now(timezone.utc)
    conteudo = await _correr_pg_dump()
    cifrado = bool(BACKUP_CHAVE_PUBLICA)
    if cifrado:
        chave_publica = cifra_backup.carregar_chave_publica(BACKUP_CHAVE_PUBLICA)
        conteudo = await asyncio.to_thread(cifra_backup.cifrar, conteudo, chave_publica)
    chave = _chave_do_backup(inicio, cifrado)
    await guardar_backup(chave, conteudo)
    apagados = await _aplicar_retencao()
    logger.info(
        "Backup concluído: %s (%d bytes, %s). %d backup(s) antigo(s) removido(s) pela retenção.",
        chave, len(conteudo), "cifrado" if cifrado else "SEM CIFRA", apagados
    )
    return {"chave": chave, "tamanho_bytes": len(conteudo), "cifrado": cifrado, "apagados_pela_retencao": apagados}
