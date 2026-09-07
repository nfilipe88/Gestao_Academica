"""Mensagens no CRM — o formulário público de leads ganha uma mensagem
opcional e a escola responde a partir do cartão do lead (ver
app/cruds/crm.py::responder_lead/listar_mensagens_lead). Módulo novo,
sem nenhum teste antes desta sessão (test_crm.py cobre a captação e a
conversão RN01, não mensagens)."""
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_comportamento import _criar_professor_com_token


async def _criar_lead_publico_e_obter_id(client, tenant_id, headers, *, email_contato: str | None = "candidata@teste.pt", mensagem: str | None = "Gostaria de saber mais sobre as vagas.") -> str:
    payload = {"nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho"}
    if email_contato is not None:
        payload["email_contato"] = email_contato
    if mensagem is not None:
        payload["mensagem"] = mensagem
    resp = await client.post(f"/api/v1/public/{tenant_id}/leads", json=payload)
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/crm/oportunidades", headers=headers)
    cartao = next(c for c in resp.json() if c["lead"]["nome_aluno_candidato"] == "Joãozinho")
    return cartao["lead"]["id"]


async def test_lead_publico_com_mensagem_fica_persistida(client):
    escola = await criar_escola_e_gestor(client, "crm-msg-persistida")
    headers = auth_headers(escola["token"])

    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
        "mensagem": "Têm vagas para o 5º ano?",
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/crm/oportunidades", headers=headers)
    cartao = next(c for c in resp.json() if c["lead"]["nome_aluno_candidato"] == "Joãozinho")
    assert cartao["lead"]["mensagem"] == "Têm vagas para o 5º ano?"


async def test_lead_publico_sem_mensagem_fica_none(client):
    escola = await criar_escola_e_gestor(client, "crm-msg-omitida")
    headers = auth_headers(escola["token"])

    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/crm/oportunidades", headers=headers)
    cartao = next(c for c in resp.json() if c["lead"]["nome_aluno_candidato"] == "Joãozinho")
    assert cartao["lead"]["mensagem"] is None


async def test_staff_responde_a_lead_com_email(client):
    escola = await criar_escola_e_gestor(client, "crm-msg-responder")
    headers = auth_headers(escola["token"])
    lead_id = await _criar_lead_publico_e_obter_id(client, escola["tenant_id"], headers)

    resp = await client.post(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=headers, json={
        "corpo": "Obrigado pelo contacto! Sim, temos vagas disponíveis."
    })
    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert corpo["autor_tipo"] == "ESCOLA"
    assert corpo["corpo"] == "Obrigado pelo contacto! Sim, temos vagas disponíveis."
    assert corpo["autor_nome"]

    resp = await client.get(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=headers)
    assert resp.status_code == 200, resp.text
    mensagens = resp.json()
    assert len(mensagens) == 1
    assert mensagens[0]["corpo"] == "Obrigado pelo contacto! Sim, temos vagas disponíveis."


async def test_responder_a_lead_sem_email_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "crm-msg-sem-email")
    headers = auth_headers(escola["token"])
    lead_id = await _criar_lead_publico_e_obter_id(client, escola["tenant_id"], headers, email_contato=None)

    resp = await client.post(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=headers, json={"corpo": "..."})
    assert resp.status_code == 400, resp.text

    resp = await client.get(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=headers)
    assert resp.json() == []


async def test_professor_nao_pode_responder_a_lead(client):
    escola = await criar_escola_e_gestor(client, "crm-msg-professor")
    headers = auth_headers(escola["token"])
    lead_id = await _criar_lead_publico_e_obter_id(client, escola["tenant_id"], headers)
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. CRM Mensagens")

    resp = await client.post(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=auth_headers(token_professor), json={"corpo": "..."})
    assert resp.status_code == 403, resp.text


async def test_mensagens_lead_isoladas_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "crm-msg-iso-a")
    escola_b = await criar_escola_e_gestor(client, "crm-msg-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    lead_id = await _criar_lead_publico_e_obter_id(client, escola_a["tenant_id"], headers_a)

    resp = await client.get(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=headers_b)
    assert resp.status_code == 404, resp.text

    resp = await client.post(f"/api/v1/crm/leads/{lead_id}/mensagens", headers=headers_b, json={"corpo": "..."})
    assert resp.status_code == 404, resp.text
