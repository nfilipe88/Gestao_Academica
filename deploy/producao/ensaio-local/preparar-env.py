#!/usr/bin/env python3
"""Prepara um ensaio LOCAL (ou no CI) da receita de produção: gera um .env com
segredos aleatórios e descartáveis e a chave pública dos backups. Nunca usar
num servidor real — lá, seguir o LEIA-ME.md.

    cd deploy/producao
    python3 ensaio-local/preparar-env.py
    ./primeiro-certificado.sh --teste-local
    docker compose -f docker-compose.yml -f docker-compose.ensaio-local.yml up -d --build
    node ensaio-local/verificar-browser.mjs

Só usa a biblioteca padrão e o openssl. Recusa substituir um .env que já exista.
"""
import json
import secrets
import subprocess
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent


def main() -> None:
    env = PASTA / ".env"
    if env.exists():
        raise SystemExit(f"{env} já existe — não o substituo.")

    privada = subprocess.run(["openssl", "genrsa", "4096"], capture_output=True, check=True).stdout
    publica = subprocess.run(["openssl", "rsa", "-pubout"], input=privada, capture_output=True, check=True).stdout
    (PASTA / "segredos").mkdir(exist_ok=True)
    (PASTA / "segredos" / "backup_publica.pem").write_bytes(publica)
    # A chave privada é descartada: este ensaio não restaura backups.

    identidades = json.loads((PASTA / "ensaio-local" / "s3.json").read_text(encoding="utf-8"))["identities"]
    aplicacao = identidades[0]["credentials"][0]
    backups = identidades[1]["credentials"][0]
    h = lambda: secrets.token_hex(24)  # noqa: E731
    env.write_text(
        f"""DOMINIO=localhost
EMAIL_CERTIFICADO=ensaio@exemplo.pt
POSTGRES_PASSWORD={h()}
APP_TENANT_DB_PASSWORD={h()}
APP_SISTEMA_DB_PASSWORD={h()}
UVICORN_WORKERS=2
DB_POOL_SIZE=15
DB_POOL_MAX_OVERFLOW=15
DB_POOL_PREAQUECER=10
REDIS_PASSWORD={h()}
JWT_SECRET_KEY={secrets.token_urlsafe(64)}
S3_BUCKET=ficheiros
S3_ENDPOINT_URL=http://s3:8333
S3_REGION=us-east-1
S3_ACCESS_KEY={aplicacao['accessKey']}
S3_SECRET_KEY={aplicacao['secretKey']}
BACKUP_S3_BUCKET=backups
BACKUP_S3_ENDPOINT_URL=http://s3:8333
BACKUP_S3_REGION=us-east-1
BACKUP_S3_ACCESS_KEY={backups['accessKey']}
BACKUP_S3_SECRET_KEY={backups['secretKey']}
PAYPAL_MODE=live
""",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Ensaio preparado: {env}")


if __name__ == "__main__":
    main()
