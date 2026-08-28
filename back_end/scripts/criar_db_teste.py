"""Cria a base de dados academic_db_test (se ainda não existir) e dá aos
roles app_tenant/app_sistema os mesmos privilégios que já têm em
academic_db (ver scripts/criar_roles_rls.sql) — para os testes (ver
tests/) correrem isolados da base de dados de desenvolvimento, sem
tocar nos dados reais usados manualmente durante o dia a dia.

Corre-se UMA VEZ por máquina de desenvolvimento, ligado como o
superuser (postgres). Os roles app_tenant/app_sistema em si já têm de
existir (roles de login são por servidor Postgres, não por base de
dados — ver criar_roles_rls.sql, corrido uma vez para academic_db).

Uso:
    python scripts/criar_db_teste.py

Depois, copiar .env.test.example para .env.test e preencher com as
mesmas passwords de app_tenant/app_sistema já usadas em .env — ver
.env.test.example para os detalhes.
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_TESTE = "academic_db_test"


def _dsn_superuser(db: str) -> str:
    # Reaproveita o utilizador/password do DATABASE_URL_MIGRACOES já
    # configurado em .env (role postgres, superuser) — só troca a base
    # de dados de destino.
    url_migracoes = os.getenv("DATABASE_URL_MIGRACOES")
    if not url_migracoes:
        raise RuntimeError("DATABASE_URL_MIGRACOES não encontrada em .env — precisa do role postgres (superuser).")
    sem_prefixo = url_migracoes.replace("postgresql+asyncpg://", "postgresql://")
    base, _, _ = sem_prefixo.rpartition("/")
    return f"{base}/{db}"


async def main():
    conn = await asyncpg.connect(_dsn_superuser("postgres"))
    try:
        existe = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", DB_TESTE)
        if not existe:
            await conn.execute(f'CREATE DATABASE "{DB_TESTE}" OWNER postgres')
            print(f"Base de dados {DB_TESTE} criada.")
        else:
            print(f"Base de dados {DB_TESTE} já existia — nada a fazer.")
    finally:
        await conn.close()

    conn2 = await asyncpg.connect(_dsn_superuser(DB_TESTE))
    try:
        await conn2.execute(f'GRANT CONNECT ON DATABASE "{DB_TESTE}" TO app_tenant, app_sistema;')
        await conn2.execute("GRANT USAGE ON SCHEMA public TO app_tenant, app_sistema;")
        await conn2.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_tenant, app_sistema;"
        )
        await conn2.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_tenant, app_sistema;")
        await conn2.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_tenant, app_sistema;"
        )
        await conn2.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO app_tenant, app_sistema;"
        )
        print("Grants aplicados. Próximo passo: alembic upgrade head com DATABASE_URL_MIGRACOES a apontar para "
              f"{DB_TESTE} (ver .env.test).")
    finally:
        await conn2.close()


if __name__ == "__main__":
    asyncio.run(main())
