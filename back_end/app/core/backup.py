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
"""
import asyncio
import logging
import os
import re
from datetime import datetime, timezone

from app.core import storage

logger = logging.getLogger("backup")

# Só precisa de apontar para o executável quando pg_dump não está no
# PATH — normal numa instalação Windows do Postgres (ver .env.example);
# em Docker/Linux com o cliente Postgres instalado, "pg_dump" já resolve.
PG_DUMP_PATH = os.getenv("PG_DUMP_PATH", "pg_dump")

# Quantos dias de backups diários manter no storage antes de apagar os
# mais antigos — sem isto, o bucket cresce para sempre com mais um
# ficheiro por dia.
BACKUP_RETENCAO_DIAS = int(os.getenv("BACKUP_RETENCAO_DIAS", "14"))

_PREFIXO_CHAVE = "_backups/"
_REGEX_NOME = re.compile(r"academic_db_(\d{8})_(\d{6})\.dump$")


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


def _chave_do_backup(quando: datetime) -> str:
    return f"{_PREFIXO_CHAVE}academic_db_{quando.strftime('%Y%m%d_%H%M%S')}.dump"


async def _aplicar_retencao() -> int:
    """Apaga backups com mais de BACKUP_RETENCAO_DIAS. Devolve quantos
    foram apagados. Chaves que não seguem o padrão esperado (ex.: um
    ficheiro colocado à mão na mesma pasta) são ignoradas em vez de
    apagadas — mais vale nunca apagar algo por engano do que ser
    demasiado agressivo na limpeza."""
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
    chave = _chave_do_backup(inicio)
    await storage.guardar_ficheiro(chave, conteudo, "application/octet-stream")
    apagados = await _aplicar_retencao()
    logger.info(
        "Backup concluído: %s (%d bytes). %d backup(s) antigo(s) removido(s) pela retenção.",
        chave, len(conteudo), apagados
    )
    return {"chave": chave, "tamanho_bytes": len(conteudo), "apagados_pela_retencao": apagados}
