"""Verifica o .env de produção contra CHECKLIST_ENV_PRODUCAO.md — sem nunca
imprimir valores de segredos, só o estado de cada regra.

Uso (no servidor, na pasta back_end):
    python scripts/verificar_env_producao.py            # lê ./.env
    python scripts/verificar_env_producao.py --env-file /caminho/.env

Sai com código 1 se algum bloqueador falhar (útil para um passo de deploy).
Não liga à base de dados nem ao storage — só olha para o ficheiro/ambiente.
"""
import argparse
import os
import sys
from urllib.parse import urlparse

from dotenv import dotenv_values

_PLACEHOLDERS = ("defina-aqui", "sua_chave", "senha", "changeme", "trocar", "example", "localhost")


def _v(env: dict, chave: str) -> str:
    return (env.get(chave) or "").strip()


def _sec_fraco(valor: str) -> bool:
    return len(valor) < 32 or any(p in valor.lower() for p in _PLACEHOLDERS)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env-file", default=".env")
    args = p.parse_args()
    if not os.path.isfile(args.env_file):
        raise SystemExit(f"{args.env_file} não existe.")
    env = {**dotenv_values(args.env_file)}

    bloqueadores: list[tuple[str, bool, str]] = []
    avisos: list[tuple[str, bool, str]] = []

    smtp_ok = all(_v(env, k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD")) and bool(_v(env, "SMTP_FROM_EMAIL") or _v(env, "SMTP_USER"))
    bloqueadores.append(("SMTP completo (ativação de conta por e-mail)", smtp_ok, "SMTP_HOST/USER/PASSWORD/FROM_EMAIL"))

    jwt = _v(env, "JWT_SECRET_KEY")
    bloqueadores.append(("JWT_SECRET_KEY forte e não-placeholder (>= 32 car.)", bool(jwt) and not _sec_fraco(jwt), "gerar com secrets.token_urlsafe(64)"))

    urls = [_v(env, k) for k in ("DATABASE_URL", "DATABASE_URL_SISTEMA", "DATABASE_URL_MIGRACOES")]
    bloqueadores.append(("3 URLs de BD definidas", all(urls), ""))
    utilizadores = [urlparse(u.replace("+asyncpg", "")).username for u in urls if u]
    bloqueadores.append(("3 roles distintos (app_tenant / app_sistema / superuser)", len(set(utilizadores)) == 3, ""))
    passwords = [urlparse(u.replace("+asyncpg", "")).password or "" for u in urls if u]
    bloqueadores.append(("Passwords da BD fortes (>= 16 car., sem placeholders)", all(len(x) >= 16 and not any(pl in x.lower() for pl in _PLACEHOLDERS) for x in passwords) and bool(passwords), ""))
    bloqueadores.append(("BD não aponta para localhost", all("localhost" not in u and "127.0.0.1" not in u for u in urls if u), "só válido se a BD for mesmo remota/gerida"))

    s3 = all(_v(env, k) for k in ("S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY"))
    bloqueadores.append(("S3 definido (backups e ficheiros fora do servidor)", s3, "S3_BUCKET/ACCESS_KEY/SECRET_KEY"))
    ep = _v(env, "S3_ENDPOINT_URL")
    bloqueadores.append(("S3 não aponta para localhost (MinIO de desenvolvimento)", "localhost" not in ep and "127.0.0.1" not in ep, ""))

    front = _v(env, "FRONTEND_URL")
    bloqueadores.append(("FRONTEND_URL é https e não é localhost", front.startswith("https://") and "localhost" not in front, ""))
    cors = _v(env, "CORS_ALLOWED_ORIGINS")
    bloqueadores.append(("CORS_ALLOWED_ORIGINS definido, sem localhost", bool(cors) and "localhost" not in cors, ""))

    avisos.append(("reCAPTCHA v3 configurado", bool(_v(env, "RECAPTCHA_SITE_KEY") and _v(env, "RECAPTCHA_SECRET_KEY")), "só rate limiting sem isto"))
    avisos.append(("Sentry configurado e ambiente = production", bool(_v(env, "SENTRY_DSN")) and _v(env, "SENTRY_ENVIRONMENT") == "production", ""))
    avisos.append(("PAYPAL_MODE não é sandbox com credenciais preenchidas", not (_v(env, "PAYPAL_CLIENT_ID") and _v(env, "PAYPAL_MODE", ) != "live"), "credenciais sandbox em produção?"))
    avisos.append(("REDIS_URL definido (obrigatório com > 1 instância)", bool(_v(env, "REDIS_URL")), "vazio só é correto com uma instância"))

    falhou = False
    print("BLOQUEADORES")
    for nome, ok, dica in bloqueadores:
        print(f"  [{'OK' if ok else 'FALHA'}] {nome}" + (f"  ({dica})" if not ok and dica else ""))
        falhou |= not ok
    print("AVISOS")
    for nome, ok, dica in avisos:
        print(f"  [{'OK' if ok else 'AVISO'}] {nome}" + (f"  ({dica})" if not ok and dica else ""))
    print("\n" + ("Há bloqueadores por resolver." if falhou else "Sem bloqueadores."))
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
