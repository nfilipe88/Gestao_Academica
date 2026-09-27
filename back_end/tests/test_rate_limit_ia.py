"""Limite de pedidos aos 3 endpoints de IA autenticados — Prof. Virtual do
aluno (api/v1/portal.py), sugestão de conteúdo do professor (api/v1/lms.py) e
trilha de recuperação do Gestor (api/v1/indicadores.py). Nenhum tinha
limitador antes (só o chat público em api/v1/publico.py tinha).

Em .env.test a ANTHROPIC_API_KEY está vazia, por isso o Prof. Virtual em si
devolve sempre 503 "não configurado" — o que serve perfeitamente para testar
o limite: ele é verificado ANTES da chamada à IA (e antes de qualquer
validação de posse do material/aluno), por isso o pedido que excede o limite
dá 429 em vez de 503, mesmo sem chave nenhuma configurada."""
import uuid

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_lms import _preparar_alocacao
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _login_aluno(client, escola, ano_letivo: int = 2026) -> tuple[dict, str]:
    dados = await _criar_aluno_matriculado_com_portal(client, auth_headers(escola["token"]), ano_letivo)
    login = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    assert login.status_code == 200, login.text
    return auth_headers(login.json()["access_token"]), dados["aluno_id"]


async def test_prof_virtual_do_aluno_tem_limite_por_utilizador(client):
    escola = await criar_escola_e_gestor(client, "limite-prof-virtual")
    headers, aluno_id = await _login_aluno(client, escola)
    corpo = {"material_id": str(uuid.uuid4()), "pergunta": "Ajudas-me?"}
    url = f"/api/v1/portal/educandos/{aluno_id}/prof-virtual"
    for _ in range(20):
        # Material inexistente -> 404 dentro do crud, mas só DEPOIS de passar o limitador.
        resp = await client.post(url, headers=headers, json=corpo)
        assert resp.status_code == 404, resp.text
    resp = await client.post(url, headers=headers, json=corpo)
    assert resp.status_code == 429, resp.text
    assert "Prof. Virtual" in resp.json()["detail"]


async def test_prof_virtual_do_aluno_limite_e_por_pessoa_nao_por_escola(client):
    """Um segundo aluno da mesma escola tem a sua própria janela — o limite não é global."""
    escola = await criar_escola_e_gestor(client, "limite-prof-virtual-2")
    headers_a, aluno_a = await _login_aluno(client, escola)
    corpo = {"material_id": str(uuid.uuid4()), "pergunta": "Ajudas-me?"}
    url_a = f"/api/v1/portal/educandos/{aluno_a}/prof-virtual"
    for _ in range(20):
        assert (await client.post(url_a, headers=headers_a, json=corpo)).status_code == 404
    assert (await client.post(url_a, headers=headers_a, json=corpo)).status_code == 429

    headers_b, aluno_b = await _login_aluno(client, escola)
    url_b = f"/api/v1/portal/educandos/{aluno_b}/prof-virtual"
    assert (await client.post(url_b, headers=headers_b, json=corpo)).status_code == 404


async def test_sugerir_conteudo_do_professor_tem_limite(client):
    escola = await criar_escola_e_gestor(client, "limite-sugerir-conteudo")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, 2026)
    corpo = {"turma_id": ctx["turma_id"], "disciplina_id": ctx["disciplina_id"], "titulo": "Introdução às frações"}
    url = "/api/v1/lms/materiais/sugestao-conteudo"
    for _ in range(20):
        resp = await client.post(url, headers=headers, json=corpo)
        assert resp.status_code == 503, resp.text
    resp = await client.post(url, headers=headers, json=corpo)
    assert resp.status_code == 429


async def test_trilha_de_recuperacao_tem_limite_por_escola_nao_por_pessoa(client):
    """Aqui é o oposto do Prof. Virtual: o limite protege o orçamento da ESCOLA
    (mesmo tenant), por isso duas pessoas da mesma Secretaria partilham a janela."""
    escola = await criar_escola_e_gestor(client, "limite-trilha")
    headers = auth_headers(escola["token"])
    matricula_id = str(uuid.uuid4())
    url = f"/api/v1/indicadores/risco-evasao/{matricula_id}/trilha-recuperacao"
    for _ in range(15):
        resp = await client.post(url, headers=headers)
        assert resp.status_code == 400, resp.text  # matrícula sem sinais de risco — mas já passou o limitador

    outro = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    resp = await client.post(url, headers=auth_headers(outro.json()["access_token"]))
    assert resp.status_code == 429, resp.text
