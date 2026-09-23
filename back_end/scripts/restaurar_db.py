"""Restaura um backup (ver app/core/backup.py) numa base de dados.

Por omissão, RECUSA restaurar por cima de "academic_db"/"academic_db_test"
— exige --confirmar-alvo-existente para isso, precisamente para nunca
apagar dados reais/de teste por um comando corrido sem pensar. O uso
normal (testar se um backup é mesmo restaurável, treinar o
procedimento) é sempre para uma base de dados nova, criada só para
esse ensaio — ver README.md, secção "Backup e Restauro".

Uso (ensaio/simulação — cria uma base nova, nunca toca nas reais):
    python scripts/restaurar_db.py --chave _backups/academic_db_20260920_140000.dump ^
        --bd-destino academic_db_drill --criar-bd

Uso (restauro a sério, disaster recovery, por cima de uma base já existente):
    python scripts/restaurar_db.py --chave _backups/academic_db_20260920_140000.dump ^
        --bd-destino academic_db --confirmar-alvo-existente
"""
import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg
from dotenv import load_dotenv
load_dotenv()

from app.core import storage

PG_RESTORE_PATH = os.getenv("PG_RESTORE_PATH", "pg_restore")

# Nunca restaurar por cima destas sem confirmação explícita — a de
# desenvolvimento e a usada pela suite de testes.
_BASES_PROTEGIDAS = {"academic_db", "academic_db_test"}


def _dsn_superuser(db: str) -> str:
    # Mesmo padrão de scripts/criar_db_teste.py — reaproveita o
    # utilizador/password do DATABASE_URL_MIGRACOES (role postgres,
    # superuser), só troca a base de dados de destino.
    url = os.getenv("DATABASE_URL_MIGRACOES")
    if not url:
        raise RuntimeError("DATABASE_URL_MIGRACOES não configurada.")
    sem_prefixo = url.replace("postgresql+asyncpg://", "postgresql://")
    base, _, _ = sem_prefixo.rpartition("/")
    return f"{base}/{db}"


async def _criar_bd_se_preciso(nome_bd: str) -> None:
    conn = await asyncpg.connect(_dsn_superuser("postgres"))
    try:
        existe = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", nome_bd)
        if not existe:
            await conn.execute(f'CREATE DATABASE "{nome_bd}" OWNER postgres')
            print(f"Base de dados '{nome_bd}' criada.")
        else:
            print(f"Base de dados '{nome_bd}' já existia — a restaurar por cima.")
    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chave", required=True, help="Chave do backup no storage, ex.: _backups/academic_db_20260920_140000.dump")
    parser.add_argument("--bd-destino", required=True, help="Nome da base de dados a restaurar")
    parser.add_argument("--criar-bd", action="store_true", help="Cria a base de dados de destino se ainda não existir")
    parser.add_argument(
        "--confirmar-alvo-existente", action="store_true",
        help="Necessário para restaurar por cima de academic_db/academic_db_test — nunca por omissão"
    )
    args = parser.parse_args()

    if args.bd_destino in _BASES_PROTEGIDAS and not args.confirmar_alvo_existente:
        raise SystemExit(
            f"'{args.bd_destino}' é uma base protegida — passe --confirmar-alvo-existente "
            "se tem mesmo a certeza (isto SUBSTITUI os dados existentes por completo)."
        )

    print(f"A descarregar '{args.chave}' do storage...")
    conteudo = await storage.obter_ficheiro(args.chave)
    if conteudo is None:
        raise SystemExit(f"Backup '{args.chave}' não encontrado no storage.")

    with tempfile.TemporaryDirectory() as pasta_temp:
        caminho_temp = Path(pasta_temp) / Path(args.chave).name
        caminho_temp.write_bytes(conteudo)
        print(f"Backup descarregado ({len(conteudo)} bytes).")

        if args.criar_bd:
            await _criar_bd_se_preciso(args.bd_destino)

        dsn = _dsn_superuser(args.bd_destino)
        print(f"A restaurar para '{args.bd_destino}' com pg_restore...")
        resultado = subprocess.run(
            [PG_RESTORE_PATH, "--clean", "--if-exists", "--no-owner", "-d", dsn, str(caminho_temp)],
            capture_output=True, text=True,
        )

    # pg_restore devolve avisos em stderr mesmo num restauro bem
    # sucedido (ex.: tentar apagar um objeto que ainda não existia na
    # base de destino) — só o código de saída decide sucesso/falha real.
    if resultado.returncode != 0:
        print(resultado.stderr)
        raise SystemExit(f"pg_restore falhou (código {resultado.returncode}).")

    print("Restauro concluído com sucesso.")
    if resultado.stderr:
        print("\nAvisos do pg_restore (normalmente inofensivos em --clean --if-exists):")
        print(resultado.stderr)


if __name__ == "__main__":
    asyncio.run(main())
