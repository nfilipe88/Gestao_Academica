"""Pré-aquecimento do pool de ligações (app/database/session.py::preaquecer_pool)
e middleware ASGI dos cabeçalhos de segurança (app/core/cabecalhos.py)."""
from app.database.session import engine, preaquecer_pool


async def test_preaquecer_pool_deixa_ligacoes_prontas_no_pool():
    await engine.dispose()
    assert engine.pool.checkedin() == 0
    abertas = await preaquecer_pool(4)
    assert abertas == 4
    assert engine.pool.checkedin() == 4, "as ligações abertas voltam ao pool, prontas a usar"
    assert engine.pool.checkedout() == 0


async def test_preaquecer_pool_zero_nao_abre_nada():
    await engine.dispose()
    assert await preaquecer_pool(0) == 0
    assert engine.pool.checkedin() == 0


async def test_preaquecer_pool_nunca_levanta_erro_se_a_base_estiver_em_baixo(monkeypatch):
    async def falha(*a, **k):
        raise ConnectionRefusedError("BD em baixo")
    monkeypatch.setattr(engine.sync_engine.pool, "connect", lambda: (_ for _ in ()).throw(ConnectionRefusedError("BD em baixo")))
    assert await preaquecer_pool(2) == 0


async def test_cabecalhos_de_seguranca_em_toda_a_api_e_sem_cache_na_autenticacao(client):
    resp = await client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "cache-control" not in resp.headers

    auth = await client.post("/api/v1/auth/login", data={"username": "nao@existe.pt", "password": "x"})
    assert auth.headers["cache-control"] == "no-store"
    assert auth.headers["x-content-type-options"] == "nosniff"


async def test_cabecalhos_nao_sobrepoem_os_que_a_rota_ja_definiu(client):
    resp = await client.get("/api/v1/public/config")
    assert list(resp.headers.keys()).count("x-content-type-options") == 1
