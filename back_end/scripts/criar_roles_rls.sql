-- Cria os dois roles Postgres de aplicação usados pelo back-end, para
-- que o Row-Level Security (isolamento_tenant_* — ver
-- alembic/versions/*) seja de facto aplicado pelo Postgres, e não
-- apenas "declarado" e ignorado por a app ligar como superuser.
--
-- Corre-se UMA VEZ por base de dados (dev, staging, produção), ligado
-- como o superuser (ex.: `postgres`). Depois disto, preencher
-- DATABASE_URL / DATABASE_URL_SISTEMA / DATABASE_URL_MIGRACOES no
-- .env com estes dois roles + o superuser (ver .env.example).
--
-- app_tenant  — SEM bypassrls: todo o tráfego normal da app passa por
--   aqui (ver app/database/session.py::obter_sessao_db). O Postgres
--   passa a filtrar de facto por tenant_id em cada policy, mesmo que
--   haja um bug numa query que se esqueça do WHERE tenant_id=....
-- app_sistema — COM bypassrls, mas SEM superuser: só para operações
--   que são, por natureza, anteriores/exteriores a um tenant concreto
--   (login, registo de escola nova, painel Super Admin, webhook de
--   pagamento, job de validade de licença). Nunca fica exposto a
--   input arbitrário do utilizador final sem passar primeiro por RBAC
--   (exigir_perfil) ou por uma verificação de assinatura (webhook).
--
-- Nenhum dos dois tem privilégios de DDL (CREATE/ALTER/DROP TABLE) —
-- as migrações continuam a correr só com o role `postgres` (superuser),
-- via DATABASE_URL_MIGRACOES.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_tenant') THEN
        CREATE ROLE app_tenant WITH LOGIN PASSWORD 'TROCAR_ESTA_PASSWORD' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_sistema') THEN
        CREATE ROLE app_sistema WITH LOGIN PASSWORD 'TROCAR_ESTA_OUTRA_PASSWORD' NOSUPERUSER BYPASSRLS;
    END IF;
END
$$;

-- Ligar à base de dados certa (ex.: \c academic_db) antes de correr o resto.
GRANT CONNECT ON DATABASE academic_db TO app_tenant, app_sistema;
GRANT USAGE ON SCHEMA public TO app_tenant, app_sistema;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_tenant, app_sistema;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_tenant, app_sistema;

-- Tabelas/sequências criadas por migrações futuras (que correm como
-- `postgres`) já nascem com este grant, sem ser preciso repetir isto
-- manualmente depois de cada `alembic upgrade head`.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_tenant, app_sistema;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_tenant, app_sistema;
