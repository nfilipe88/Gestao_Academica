"""
Fase 4 (armazenamento) — logótipo da escola (Configurações) e anexo de
Comunicado: upload/download autenticado e isolamento entre tenants.

Corre sem S3_BUCKET configurado (fallback de disco local, ver
app/core/storage.py) — o mesmo comportamento que um ambiente de
desenvolvimento sem MinIO/S3 tem.
"""
from tests.conftest import auth_headers, criar_escola_e_gestor

_PNG_FALSO = b"\x89PNG\r\n\x1a\n" + b"conteudo-de-teste-para-o-logotipo"


async def test_logotipo_upload_download_e_remover(client):
    gestor = await criar_escola_e_gestor(client, "logo")
    headers = auth_headers(gestor["token"])

    # Antes de qualquer upload: sem logótipo.
    resp = await client.get("/api/v1/configuracoes", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["tem_logotipo"] is False

    resp = await client.get("/api/v1/configuracoes/logotipo", headers=headers)
    assert resp.status_code == 404

    # Upload.
    resp = await client.put(
        "/api/v1/configuracoes/logotipo", headers=headers,
        files={"ficheiro": ("logo.png", _PNG_FALSO, "image/png")}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["tem_logotipo"] is True

    # Download devolve exatamente os mesmos bytes.
    resp = await client.get("/api/v1/configuracoes/logotipo", headers=headers)
    assert resp.status_code == 200
    assert resp.content == _PNG_FALSO
    assert resp.headers["content-type"] == "image/png"

    # Substituir por um novo ficheiro — continua a haver só 1 logótipo.
    novo_conteudo = _PNG_FALSO + b"-v2"
    resp = await client.put(
        "/api/v1/configuracoes/logotipo", headers=headers,
        files={"ficheiro": ("logo2.png", novo_conteudo, "image/png")}
    )
    assert resp.status_code == 200
    resp = await client.get("/api/v1/configuracoes/logotipo", headers=headers)
    assert resp.content == novo_conteudo

    # Remover.
    resp = await client.delete("/api/v1/configuracoes/logotipo", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["tem_logotipo"] is False
    resp = await client.get("/api/v1/configuracoes/logotipo", headers=headers)
    assert resp.status_code == 404


async def test_logotipo_rejeita_tipo_de_ficheiro_invalido(client):
    gestor = await criar_escola_e_gestor(client, "logotipoinvalido")
    headers = auth_headers(gestor["token"])

    resp = await client.put(
        "/api/v1/configuracoes/logotipo", headers=headers,
        files={"ficheiro": ("relatorio.pdf", b"%PDF-1.4 conteudo", "application/pdf")}
    )
    assert resp.status_code == 400
    assert "não aceite" in resp.json()["detail"].lower()


async def test_comunicado_anexo_upload_download_e_isolamento_entre_escolas(client):
    escola_a = await criar_escola_e_gestor(client, "anexoA")
    escola_b = await criar_escola_e_gestor(client, "anexoB")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])

    resp = await client.post("/api/v1/comunicados", headers=headers_a, json={
        "tipo": "COMUNICADO", "titulo": "Circular de teste", "corpo": "Ver anexo.",
        "destinatario_tipo": "ESCOLA",
    })
    assert resp.status_code == 201, resp.text
    comunicado_id = resp.json()["id"]

    conteudo_anexo = b"conteudo-do-pdf-de-teste-da-circular"
    resp = await client.put(
        f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers_a,
        files={"ficheiro": ("circular.pdf", conteudo_anexo, "application/pdf")}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["nome_original"] == "circular.pdf"

    # A própria escola consegue descarregar de volta, com o mesmo conteúdo.
    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers_a)
    assert resp.status_code == 200
    assert resp.content == conteudo_anexo

    # A lista de comunicados da escola A já assinala tem_anexo=True.
    resp = await client.get("/api/v1/comunicados", headers=headers_a)
    assert resp.status_code == 200
    item = next(i for i in resp.json()["items"] if i["id"] == comunicado_id)
    assert item["tem_anexo"] is True

    # Isolamento entre tenants: a escola B nem sequer vê o comunicado (404),
    # apesar de ter o mesmo perfil GESTOR/staff.
    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers_b)
    assert resp.status_code == 404


async def test_comunicado_sem_anexo_devolve_404(client):
    gestor = await criar_escola_e_gestor(client, "semanexo")
    headers = auth_headers(gestor["token"])

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "Sem anexo", "corpo": "Só texto.",
        "destinatario_tipo": "ESCOLA",
    })
    assert resp.status_code == 201, resp.text
    comunicado_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers)
    assert resp.status_code == 404
