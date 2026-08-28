"""Teste de fumo — confirma que a app arranca e responde antes de
qualquer teste mais elaborado correr."""


async def test_health_check(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
