"""CRM — captação pública de leads (RN03) e assistente de matrícula
self-service (candidatura com documentos) — ver app/cruds/crm.py.

Cobertura mínima do que ainda não estava testado: o CRM (Kanban,
funil, RN01) não tinha nenhum teste próprio antes desta funcionalidade."""
import io

from tests.conftest import auth_headers, criar_escola_e_gestor

# PNG 1x1 mínimo válido — mesmo ficheiro usado em test_site_publico.py.
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


async def test_lead_publico_devolve_id_da_candidatura(client):
    escola = await criar_escola_e_gestor(client, "crm-lead-id")
    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"]


async def test_lead_publico_aceita_data_nascimento_e_desbloqueia_rn01(client):
    """Antes desta funcionalidade, o formulário público nunca enviava
    data_nascimento_candidato — a conversão RN01 ficava sempre bloqueada
    até a Secretaria a preencher à mão. Agora o assistente de matrícula
    já a envia na candidatura."""
    escola = await criar_escola_e_gestor(client, "crm-lead-nascimento")
    headers = auth_headers(escola["token"])

    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
        "data_nascimento_candidato": "2015-03-10", "aceitou_regulamento": True,
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/crm/oportunidades", headers=headers)
    cartao = next(c for c in resp.json() if c["lead"]["nome_aluno_candidato"] == "Joãozinho")
    assert cartao["lead"]["data_nascimento_candidato"] == "2015-03-10"
    assert cartao["lead"]["aceitou_regulamento"] is True

    # Move para a etapa "Matriculado" (eh_etapa_ganho) — sem a data de
    # nascimento isto falharia com 400 (ver _converter_lead_em_aluno).
    resp = await client.get("/api/v1/crm/funil", headers=headers)
    etapa_matriculado = next(e for e in resp.json() if e["eh_etapa_ganho"])
    resp = await client.patch(f"/api/v1/crm/oportunidades/{cartao['id']}/mover", headers=headers,
                               json={"nova_etapa_id": etapa_matriculado["id"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["oportunidade"]["aluno_gerado_id"]


async def test_candidato_anexa_e_remove_documento(client):
    escola = await criar_escola_e_gestor(client, "crm-lead-doc")
    headers = auth_headers(escola["token"])

    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    lead_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/public/{escola['tenant_id']}/leads/{lead_id}/documentos", params={"tipo": "BI"},
        files={"ficheiro": ("bi.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    documentos = resp.json()["documentos"]
    assert len(documentos) == 1
    assert documentos[0]["tipo"] == "BI"
    doc_id = documentos[0]["id"]

    # A Secretaria consegue ver o documento (data URI, só quando pedido).
    resp = await client.get(f"/api/v1/crm/leads/{lead_id}/documentos/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:image/png;base64,")

    resp = await client.delete(f"/api/v1/public/{escola['tenant_id']}/leads/{lead_id}/documentos/{doc_id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["documentos"] == []


async def test_documento_rejeita_tipo_invalido(client):
    escola = await criar_escola_e_gestor(client, "crm-lead-doc-tipo-invalido")
    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    lead_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/public/{escola['tenant_id']}/leads/{lead_id}/documentos", params={"tipo": "PASSAPORTE"},
        files={"ficheiro": ("bi.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 400


async def test_documento_rejeita_ficheiro_nao_suportado(client):
    escola = await criar_escola_e_gestor(client, "crm-lead-doc-ficheiro-invalido")
    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    lead_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/public/{escola['tenant_id']}/leads/{lead_id}/documentos", params={"tipo": "BI"},
        files={"ficheiro": ("nota.txt", io.BytesIO(b"nao e um documento"), "text/plain")}
    )
    assert resp.status_code == 400


async def test_documentos_isolados_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "crm-lead-doc-iso-a")
    escola_b = await criar_escola_e_gestor(client, "crm-lead-doc-iso-b")

    resp = await client.post(f"/api/v1/public/{escola_a['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    lead_id = resp.json()["id"]

    # Tentar anexar um documento a esse lead através do tenant errado falha.
    resp = await client.post(
        f"/api/v1/public/{escola_b['tenant_id']}/leads/{lead_id}/documentos", params={"tipo": "BI"},
        files={"ficheiro": ("bi.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 404

    # A Secretaria da escola B também não consegue ver documentos do lead da escola A.
    resp = await client.post(
        f"/api/v1/public/{escola_a['tenant_id']}/leads/{lead_id}/documentos", params={"tipo": "BI"},
        files={"ficheiro": ("bi.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    doc_id = resp.json()["documentos"][0]["id"]
    resp = await client.get(f"/api/v1/crm/leads/{lead_id}/documentos/{doc_id}", headers=auth_headers(escola_b["token"]))
    assert resp.status_code == 404
