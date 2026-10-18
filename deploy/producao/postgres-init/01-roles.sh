#!/bin/bash
# Corre UMA vez, quando o volume do Postgres é criado (docker-entrypoint-initdb.d).
# Cria as duas roles do Row-Level Security (ver back_end/scripts/criar_roles_rls.sql)
# com as passwords do .env — nunca passwords fixas no repositório.
#  - app_tenant: a aplicação no dia a dia, SEM BYPASSRLS (cada escola só vê os seus dados);
#  - app_sistema: login/registo/jobs entre escolas, com BYPASSRLS e filtros explícitos.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v tenant_pw="$APP_TENANT_DB_PASSWORD" -v sistema_pw="$APP_SISTEMA_DB_PASSWORD" <<'SQL'
CREATE ROLE app_tenant WITH LOGIN PASSWORD :'tenant_pw' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE app_sistema WITH LOGIN PASSWORD :'sistema_pw' NOSUPERUSER BYPASSRLS;

GRANT CONNECT ON DATABASE academic_db TO app_tenant, app_sistema;
GRANT USAGE ON SCHEMA public TO app_tenant, app_sistema;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_tenant, app_sistema;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_tenant, app_sistema;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_tenant, app_sistema;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_tenant, app_sistema;
SQL
