"""Respostas a Comunicados — encarregado/aluno responde no Portal a um
comunicado, a escola vê as respostas em Comunicações (ver
app/cruds/comunicacoes.py::responder_comunicado/listar_respostas_comunicado,
app/cruds/portal.py::responder_comunicado_do_educando). Módulo novo,
sem nenhum teste antes desta sessão."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _criar_comunicado_para_turma(client, headers, dados: dict) -> str:
    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "Reunião de Pais", "corpo": "Reunião dia 10.",
        "destinatario_tipo": "TURMA", "destinatario_turma_id": dados["turma_id"]
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_responsavel_responde_a_comunicado_do_seu_educando(client):
    escola = await criar_escola_e_gestor(client, "resposta-responsavel")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    comunicado_id = await _criar_comunicado_para_turma(client, headers, dados)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_resp = auth_headers(resp.json()["access_token"])

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/comunicados/{comunicado_id}/respostas",
        headers=headers_resp, json={"corpo": "Obrigado pelo aviso, estarei presente."}
    )
    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert corpo["aluno_id"] == dados["aluno_id"]
    assert corpo["corpo"] == "Obrigado pelo aviso, estarei presente."
    assert corpo["autor_nome"]

    # A escola vê a resposta.
    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/respostas", headers=headers)
    assert resp.status_code == 200, resp.text
    respostas = resp.json()
    assert len(respostas) == 1
    assert respostas[0]["corpo"] == "Obrigado pelo aviso, estarei presente."

    # E foi notificada dentro da app.
    resp = await client.get("/api/v1/notificacoes", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(n["tipo"] == "COMUNICADO_RESPOSTA" for n in resp.json())


async def test_aluno_tambem_pode_responder_aos_seus_comunicados(client):
    escola = await criar_escola_e_gestor(client, "resposta-aluno")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    comunicado_id = await _criar_comunicado_para_turma(client, headers, dados)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    headers_aluno = auth_headers(resp.json()["access_token"])

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/comunicados/{comunicado_id}/respostas",
        headers=headers_aluno, json={"corpo": "Recebido."}
    )
    assert resp.status_code == 201, resp.text


async def test_responsavel_nao_pode_responder_por_aluno_que_nao_e_seu(client):
    escola = await criar_escola_e_gestor(client, "resposta-nao-autorizada")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados_a = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    dados_b = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    comunicado_id = await _criar_comunicado_para_turma(client, headers, dados_a)

    # Login do responsável do aluno B, a tentar responder em nome do aluno A.
    resp = await client.post("/api/v1/auth/login", data={"username": dados_b["email_responsavel"], "password": dados_b["senha"]})
    headers_resp_b = auth_headers(resp.json()["access_token"])

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados_a['aluno_id']}/comunicados/{comunicado_id}/respostas",
        headers=headers_resp_b, json={"corpo": "Não devia funcionar."}
    )
    assert resp.status_code == 403, resp.text


async def test_professor_consegue_ler_respostas_do_comunicado_que_enviou(client):
    escola = await criar_escola_e_gestor(client, "resposta-professor-le")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    _, token_professor = await _criar_professor_com_token(client, headers, f"Prof. Respostas {sufixo_unico()}")

    comunicado_id = await _criar_comunicado_para_turma(client, headers, dados)

    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/respostas", headers=auth_headers(token_professor))
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


async def test_respostas_isoladas_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "resposta-iso-a")
    escola_b = await criar_escola_e_gestor(client, "resposta-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    ano_letivo = date.today().year
    dados_a = await _criar_aluno_matriculado_com_portal(client, headers_a, ano_letivo)
    comunicado_id = await _criar_comunicado_para_turma(client, headers_a, dados_a)

    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/respostas", headers=headers_b)
    assert resp.status_code == 404, resp.text


async def test_responder_a_comunicado_inexistente_da_404(client):
    escola = await criar_escola_e_gestor(client, "resposta-comunicado-inexistente")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_resp = auth_headers(resp.json()["access_token"])

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/comunicados/00000000-0000-0000-0000-000000000000/respostas",
        headers=headers_resp, json={"corpo": "..."}
    )
    assert resp.status_code == 404, resp.text
