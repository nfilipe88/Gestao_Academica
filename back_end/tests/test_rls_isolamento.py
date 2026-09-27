"""Isolamento multi-tenant — o requisito mais crítico desta plataforma
(o próprio código já foi corrigido uma vez por o RLS estar decorativo,
ver commit 13a061d). Estes testes existem para essa regressão nunca
mais passar despercebida."""
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tests.conftest import auth_headers, criar_escola_e_gestor


async def _query_como_tenant(tenant_id: str, sql: str, params: dict) -> list:
    """Abre uma ligação como app_tenant (a mesma role usada em produção,
    COM RLS ativo) e corre `sql` com app.current_tenant_id definido para
    tenant_id — espelha app/database/session.py::obter_sessao_db, mas
    sem passar pelo FastAPI, para testar a policy diretamente em vez de
    testar só se o crud lembrou de filtrar."""
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as conn:
            async with AsyncSession(bind=conn, expire_on_commit=False) as sessao:
                await sessao.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, false)"), {"tid": tenant_id}
                )
                resultado = await sessao.execute(text(sql), params)
                return resultado.fetchall()
    finally:
        await engine.dispose()


async def test_rls_bloqueia_leitura_cross_tenant_mesmo_sem_filtro_na_query(client):
    """O teste mais importante desta suite: prova que o isolamento entre
    escolas não depende só do WHERE tenant_id=... escrito em cada crud —
    o próprio Postgres recusa devolver a linha quando a sessão está
    identificada como outro tenant, mesmo perguntando pelo id exato,
    de propósito sem nenhum filtro de tenant na query.
    """
    escola_a = await criar_escola_e_gestor(client, "rls-a")
    escola_b = await criar_escola_e_gestor(client, "rls-b")

    resp = await client.post(
        "/api/v1/academico/cursos", json={"nome": "Curso Secreto da Escola A"},
        headers=auth_headers(escola_a["token"])
    )
    assert resp.status_code == 201, resp.text
    curso_id = resp.json()["id"]

    # Como o próprio tenant A: a linha existe e é visível.
    linhas_a = await _query_como_tenant(
        escola_a["tenant_id"], "SELECT id FROM curso WHERE id = :id", {"id": curso_id}
    )
    assert len(linhas_a) == 1

    # Como o tenant B, SEM filtrar por tenant_id na query — se isto
    # devolver alguma coisa, a policy de RLS não está a bloquear.
    linhas_b = await _query_como_tenant(
        escola_b["tenant_id"], "SELECT id FROM curso WHERE id = :id", {"id": curso_id}
    )
    assert len(linhas_b) == 0, (
        "FALHA DE ISOLAMENTO: a escola B conseguiu ler uma linha da escola A "
        "diretamente na base de dados — a policy de RLS não está a bloquear."
    )


async def test_listagem_de_cursos_nao_mistura_escolas(client):
    """Camada de aplicação (o WHERE explícito nos cruds) — mais superficial
    que o teste acima, mas é o que os utilizadores reais experimentam
    no dia a dia."""
    escola_a = await criar_escola_e_gestor(client, "list-a")
    escola_b = await criar_escola_e_gestor(client, "list-b")

    await client.post("/api/v1/academico/cursos", json={"nome": "Só da A"}, headers=auth_headers(escola_a["token"]))
    await client.post("/api/v1/academico/cursos", json={"nome": "Só da B"}, headers=auth_headers(escola_b["token"]))

    resp_a = await client.get("/api/v1/academico/cursos", headers=auth_headers(escola_a["token"]))
    assert resp_a.status_code == 200
    nomes_a = [c["nome"] for c in resp_a.json()]
    assert "Só da A" in nomes_a
    assert "Só da B" not in nomes_a

    resp_b = await client.get("/api/v1/academico/cursos", headers=auth_headers(escola_b["token"]))
    assert resp_b.status_code == 200
    nomes_b = [c["nome"] for c in resp_b.json()]
    assert "Só da B" in nomes_b
    assert "Só da A" not in nomes_b


async def test_todas_as_tabelas_com_tenant_id_tem_rls_ativo_e_pelo_menos_uma_policy():
    """Rede de segurança contra a MESMA lição já aprendida uma vez (RLS
    'declarado' numa migração mas sem efeito real — ver o commit citado no
    topo do ficheiro): os dois testes acima só provam isolamento na tabela
    `curso`; este cobre TODAS as tabelas com tenant_id de uma vez, direto do
    catálogo do Postgres (não confia no código Python nem em cada migração
    se lembrar) — se uma tabela nova entrar sem RLS, ou sem nenhuma policy
    (RLS "ligado" mas sem regra nenhuma bloqueia tudo silenciosamente, o que
    é seguro mas quase de certeza um esquecimento), este teste falha sozinho,
    sem ninguém ter de se lembrar de escrever um teste dedicado para ela.

    Liga como o role de migrações (superuser) só para LER o catálogo —
    nunca para tocar em dados de nenhum tenant.
    """
    engine = create_async_engine(os.environ["DATABASE_URL_MIGRACOES"])
    try:
        async with engine.connect() as conn:
            tabelas = (await conn.execute(text("""
                SELECT c.relname AS tabela, c.relrowsecurity AS rls_ativo,
                       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname) AS n_policies
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                  AND EXISTS (
                      SELECT 1 FROM information_schema.columns col
                      WHERE col.table_schema = 'public' AND col.table_name = c.relname AND col.column_name = 'tenant_id'
                  )
                ORDER BY c.relname
            """))).all()
    finally:
        await engine.dispose()

    assert tabelas, "nenhuma tabela com coluna tenant_id encontrada — teste desatualizado ou ligado à BD errada"

    sem_rls = [t.tabela for t in tabelas if not t.rls_ativo]
    assert not sem_rls, (
        "FALHA DE ISOLAMENTO: tabela(s) com tenant_id mas SEM Row-Level Security ativo — "
        f"acrescentar ENABLE ROW LEVEL SECURITY (ver o padrão TABELAS_RLS de qualquer migração recente): {sem_rls}"
    )

    sem_policy = [t.tabela for t in tabelas if t.n_policies == 0]
    assert not sem_policy, (
        "RLS ativo mas SEM NENHUMA policy definida — bloqueia tudo por omissão (não é uma fuga de "
        f"dados), mas quase de certeza um esquecimento da CREATE POLICY: {sem_policy}"
    )
