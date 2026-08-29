"""Trilha de auditoria GERAL (quem/quando/o quê foi criado, alterado ou
apagado) — ver app/core/auditoria.py (listener automático) e
app/api/v1/auditoria.py (leitura). Diferente de test_usuarios.py (RBAC)
e de qualquer teste de notas — isto cobre entidades quaisquer.
"""
from tests.conftest import auth_headers, criar_escola_e_gestor


async def test_criar_conta_gera_registo_criado_na_auditoria(client):
    escola = await criar_escola_e_gestor(client, "auditoria-criado")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers, json={
        "nome_completo": "Secretária Auditada", "email": f"sec.aud.{escola['nif']}@teste.pt", "palavra_passe": "SenhaTeste123!"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/auditoria", headers=headers, params={"entidade": "usuario", "acao": "CRIADO"})
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["total"] >= 1
    registo = corpo["items"][0]
    assert registo["acao"] == "CRIADO"
    assert registo["entidade"] == "usuario"
    assert registo["autor_id"] == escola["usuario_id"]
    assert registo["autor_nome"] == "Gestor auditoria-criado"
    # Snapshot de CRIADO: sem hash de senha em claro no log.
    assert "senha_hash" not in registo["alteracoes"]
    assert registo["alteracoes"]["nome_completo"] == "Secretária Auditada"


async def test_suspender_conta_gera_registo_alterado_com_antes_depois(client):
    escola = await criar_escola_e_gestor(client, "auditoria-alterado")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers, json={
        "nome_completo": "Secretária B", "email": f"sec.b.{escola['nif']}@teste.pt", "palavra_passe": "SenhaTeste123!"
    })
    secretaria_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/usuarios/{secretaria_id}/ativo", headers=headers, json={"ativo": False})
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/v1/auditoria", headers=headers, params={"entidade_id": secretaria_id, "acao": "ALTERADO"})
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["total"] >= 1
    alteracoes = corpo["items"][0]["alteracoes"]
    assert alteracoes["ativo"] == {"antes": True, "depois": False}
    # Só o campo que mudou fica registado — não o resto das colunas inalteradas.
    assert "nome_completo" not in alteracoes


async def test_apagar_template_gera_registo_apagado(client):
    escola = await criar_escola_e_gestor(client, "auditoria-apagado")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/documentos/templates/CERTIFICADO", headers=headers, json={
        "corpo_html": "<p>Certifico que {{ aluno_nome }} concluiu.</p>"
    })
    assert resp.status_code == 200, resp.text

    resp = await client.delete("/api/v1/documentos/templates/CERTIFICADO", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/v1/auditoria", headers=headers, params={
        "entidade": "template_documento_personalizado", "acao": "APAGADO"
    })
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["total"] >= 1
    assert corpo["items"][0]["alteracoes"]["tipo_documento"] == "CERTIFICADO"


async def test_auditoria_e_isolada_por_tenant(client):
    """Gestor de uma escola nunca vê ações de auditoria de outra escola."""
    escola_a = await criar_escola_e_gestor(client, "auditoria-iso-a")
    escola_b = await criar_escola_e_gestor(client, "auditoria-iso-b")

    resp = await client.post("/api/v1/usuarios/secretaria", headers=auth_headers(escola_a["token"]), json={
        "nome_completo": "Só da Escola A", "email": f"soa.{escola_a['nif']}@teste.pt", "palavra_passe": "SenhaTeste123!"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/auditoria", headers=auth_headers(escola_b["token"]))
    assert resp.status_code == 200, resp.text
    nomes = [
        item["alteracoes"].get("nome_completo") for item in resp.json()["items"]
        if item["entidade"] == "usuario" and item.get("alteracoes")
    ]
    assert "Só da Escola A" not in nomes


async def test_auditoria_restrita_a_gestor(client):
    """Secretaria não pode ver a trilha de auditoria — mesma sensibilidade de /usuarios/auditoria."""
    escola = await criar_escola_e_gestor(client, "auditoria-rbac")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers, json={
        "nome_completo": "Secretária C", "email": f"sec.c.{escola['nif']}@teste.pt", "palavra_passe": "SenhaTeste123!"
    })
    resp_login = await client.post("/api/v1/auth/login", data={
        "username": f"sec.c.{escola['nif']}@teste.pt", "password": "SenhaTeste123!"
    })
    token_secretaria = resp_login.json()["access_token"]

    resp = await client.get("/api/v1/auditoria", headers=auth_headers(token_secretaria))
    assert resp.status_code == 403
