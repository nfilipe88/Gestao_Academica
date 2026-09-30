"""Assinantes de Documentos — atribuição administrativa de quem assina
cada tipo de documento formal (app/database/models.py::AssinanteDocumento).
Decisão da escola, nunca de quem gera o PDF — ver app/core/assinaturas.py
para a leitura usada na geração real (tests/test_documentos_pdf_assinatura.py
cobre o render em si; tests/test_documentos_solicitacoes.py,
tests/test_recibo_pagamento.py e tests/test_transferencias.py cobrem o
wiring ponta a ponta)."""
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_comportamento import _criar_professor_com_token
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def test_gestor_adiciona_e_lista_assinante(client):
    escola = await criar_escola_e_gestor(client, "assinantes-crud")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "CERTIFICADO", "usuario_id": escola["usuario_id"], "cargo": "Diretora Geral", "ordem": 0,
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["cargo"] == "Diretora Geral"
    assert resp.json()["nome_usuario"]

    resp = await client.get("/api/v1/configuracoes/assinantes-documentos", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1 and resp.json()[0]["tipo_documento"] == "CERTIFICADO"


async def test_gestor_atualiza_cargo_e_ordem(client):
    escola = await criar_escola_e_gestor(client, "assinantes-atualizar")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "BOLETIM", "usuario_id": escola["usuario_id"], "cargo": "Provisório", "ordem": 5,
    })
    assinante_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/configuracoes/assinantes-documentos/{assinante_id}", headers=headers, json={
        "cargo": "Diretora Pedagógica", "ordem": 0,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["cargo"] == "Diretora Pedagógica" and resp.json()["ordem"] == 0


async def test_gestor_remove_assinante(client):
    escola = await criar_escola_e_gestor(client, "assinantes-remover")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "BOLETIM", "usuario_id": escola["usuario_id"], "cargo": "Diretor", "ordem": 0,
    })
    assinante_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/configuracoes/assinantes-documentos/{assinante_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/configuracoes/assinantes-documentos", headers=headers)
    assert resp.json() == []


async def test_rejeita_tipo_documento_invalido(client):
    escola = await criar_escola_e_gestor(client, "assinantes-tipo-invalido")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "OUTRO", "usuario_id": escola["usuario_id"], "cargo": "X", "ordem": 0,
    })
    assert resp.status_code == 422


async def test_rejeita_usuario_id_de_outro_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "assinantes-iso-a")
    escola_b = await criar_escola_e_gestor(client, "assinantes-iso-b")
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=auth_headers(escola_a["token"]), json={
        "tipo_documento": "CERTIFICADO", "usuario_id": escola_b["usuario_id"], "cargo": "X", "ordem": 0,
    })
    assert resp.status_code == 404


async def test_rejeita_perfil_aluno_responsavel_como_assinante(client):
    """Só faz sentido de negócio staff assinar — um ALUNO/RESPONSAVEL
    nunca pode ser designado assinante de um documento."""
    from datetime import date
    escola = await criar_escola_e_gestor(client, "assinantes-rejeita-familia")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    resp_usuario_id = resp.json()["utilizador"]["id"]

    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "CERTIFICADO", "usuario_id": resp_usuario_id, "cargo": "X", "ordem": 0,
    })
    assert resp.status_code == 400


async def test_rejeita_mesmo_usuario_duas_vezes_no_mesmo_tipo(client):
    escola = await criar_escola_e_gestor(client, "assinantes-duplicado")
    headers = auth_headers(escola["token"])
    payload = {"tipo_documento": "BOLETIM", "usuario_id": escola["usuario_id"], "cargo": "X", "ordem": 0}
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json=payload)
    assert resp.status_code == 400


async def test_apenas_gestor_gere_recebe_403(client):
    escola = await criar_escola_e_gestor(client, "assinantes-rbac")
    headers = auth_headers(escola["token"])
    _, token_prof = await _criar_professor_com_token(client, headers, "Prof. Assinantes")
    headers_prof = auth_headers(token_prof)

    resp = await client.get("/api/v1/configuracoes/assinantes-documentos", headers=headers_prof)
    assert resp.status_code == 403
    resp = await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers_prof, json={
        "tipo_documento": "CERTIFICADO", "usuario_id": escola["usuario_id"], "cargo": "X", "ordem": 0,
    })
    assert resp.status_code == 403


async def test_isolamento_por_tenant_na_listagem(client):
    escola_a = await criar_escola_e_gestor(client, "assinantes-lista-a")
    escola_b = await criar_escola_e_gestor(client, "assinantes-lista-b")
    headers_a, headers_b = auth_headers(escola_a["token"]), auth_headers(escola_b["token"])
    await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers_a, json={
        "tipo_documento": "CERTIFICADO", "usuario_id": escola_a["usuario_id"], "cargo": "X", "ordem": 0,
    })
    resp = await client.get("/api/v1/configuracoes/assinantes-documentos", headers=headers_b)
    assert resp.json() == []


async def test_ordem_e_respeitada_na_listagem(client):
    """2 assinantes no mesmo tipo — listar_assinantes devolve por
    `ordem`, a mesma ordenação usada por obter_assinantes_documento na
    geração real do PDF (mesma query, ver app/cruds/assinantes_documento.py
    e app/core/assinaturas.py)."""
    escola = await criar_escola_e_gestor(client, "assinantes-ordem")
    headers = auth_headers(escola["token"])
    _, token_prof = await _criar_professor_com_token(client, headers, "Prof. Ordem")
    resp = await client.get("/api/v1/usuarios", headers=headers)
    prof_id = next(u["id"] for u in resp.json()["items"] if u["perfil_acesso"] == "PROFESSOR")

    await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "CERTIFICADO", "usuario_id": prof_id, "cargo": "Pedagógico", "ordem": 1,
    })
    await client.post("/api/v1/configuracoes/assinantes-documentos", headers=headers, json={
        "tipo_documento": "CERTIFICADO", "usuario_id": escola["usuario_id"], "cargo": "Geral", "ordem": 0,
    })

    resp = await client.get("/api/v1/configuracoes/assinantes-documentos", headers=headers)
    cargos = [a["cargo"] for a in resp.json()]
    assert cargos == ["Geral", "Pedagógico"]
