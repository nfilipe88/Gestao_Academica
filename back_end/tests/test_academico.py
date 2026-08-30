"""Módulo Académico — Cursos (ver app/cruds/academico.py).

Cobertura mínima do que ainda não estava testado: criar/listar já era
exercitado indiretamente por tests/test_site_publico.py, mas editar um
curso é funcionalidade nova (antes só existia criar/listar)."""
from tests.conftest import auth_headers, criar_escola_e_gestor


async def test_gestor_renomeia_curso(client):
    escola = await criar_escola_e_gestor(client, "academico-curso-editar")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/academico/cursos", headers=headers, json={"nome": "Ensino Básico"})
    assert resp.status_code == 201, resp.text
    curso_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/academico/cursos/{curso_id}", headers=headers, json={"nome": "Ensino Fundamental"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["nome"] == "Ensino Fundamental"

    resp = await client.get("/api/v1/academico/cursos", headers=headers)
    nomes = [c["nome"] for c in resp.json()]
    assert "Ensino Fundamental" in nomes
    assert "Ensino Básico" not in nomes


async def test_renomear_curso_com_nome_vazio_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "academico-curso-vazio")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/academico/cursos", headers=headers, json={"nome": "Curso X"})
    curso_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/academico/cursos/{curso_id}", headers=headers, json={"nome": ""})
    assert resp.status_code == 422


async def test_renomear_curso_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "academico-curso-iso-a")
    escola_b = await criar_escola_e_gestor(client, "academico-curso-iso-b")
    resp = await client.post("/api/v1/academico/cursos", headers=auth_headers(escola_a["token"]), json={"nome": "Curso A"})
    curso_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/academico/cursos/{curso_id}", headers=auth_headers(escola_b["token"]), json={"nome": "Roubado"})
    assert resp.status_code == 404


async def test_renomear_curso_inexistente_da_404(client):
    escola = await criar_escola_e_gestor(client, "academico-curso-404")
    import uuid
    resp = await client.put(f"/api/v1/academico/cursos/{uuid.uuid4()}", headers=auth_headers(escola["token"]), json={"nome": "X"})
    assert resp.status_code == 404
