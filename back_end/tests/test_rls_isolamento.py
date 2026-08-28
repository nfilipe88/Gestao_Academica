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
