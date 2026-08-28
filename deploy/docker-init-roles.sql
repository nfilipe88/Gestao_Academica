-- Corre automaticamente na primeira vez que o volume do Postgres do
-- docker-compose é criado (montado em /docker-entrypoint-initdb.d/) —
-- cria os roles app_tenant/app_sistema com as passwords que o serviço
-- "backend" do docker-compose.yml espera (ver DATABASE_URL/
-- DATABASE_URL_SISTEMA nesse serviço), para o Row-Level Security
-- (isolamento_tenant_* — ver back_end/alembic/versions/*) ser aplicado
-- a sério, do mesmo modo que em desenvolvimento/produção.
--
-- Só para o ambiente local via docker-compose. Em staging/produção
-- reais, seguir back_end/scripts/criar_roles_rls.sql com passwords
-- próprias — nunca estas.
CREATE ROLE app_tenant WITH LOGIN PASSWORD 'app_tenant_docker' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE app_sistema WITH LOGIN PASSWORD 'app_sistema_docker' NOSUPERUSER BYPASSRLS;

GRANT CONNECT ON DATABASE academic_db TO app_tenant, app_sistema;
GRANT USAGE ON SCHEMA public TO app_tenant, app_sistema;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_tenant, app_sistema;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_tenant, app_sistema;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_tenant, app_sistema;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_tenant, app_sistema;
