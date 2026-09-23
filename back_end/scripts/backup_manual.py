"""Dispara um backup imediatamente, fora do agendamento diário (03:00,
ver app/core/scheduler.py) — para testar a configuração (S3, PG_DUMP_PATH)
sem esperar pelo relógio, ou para tirar um backup extra antes de uma
operação arriscada (ex.: uma migração grande em produção).

Uso:
    python scripts/backup_manual.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.backup import executar_backup_diario


async def main():
    resultado = await executar_backup_diario()
    print(f"Backup concluído: {resultado['chave']} ({resultado['tamanho_bytes']} bytes).")
    if resultado["apagados_pela_retencao"]:
        print(f"{resultado['apagados_pela_retencao']} backup(s) antigo(s) removido(s) pela política de retenção.")


if __name__ == "__main__":
    asyncio.run(main())
