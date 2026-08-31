"""Comunicações (Comunicados/Convocatórias) — ver app/cruds/comunicacoes.py.
Nenhum teste próprio antes desta sessão."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _criar_aluno_matriculado_com_email_contacto(client, headers, ano_letivo: int) -> dict:
    """Como _criar_aluno_matriculado_com_portal, mas preenchendo também
    o e-mail de contacto do responsável (ResponsavelFinanceiroLegal.
    email — campo separado do e-mail de login, único usado para
    resolver destinatários de e-mail em Comunicações). Não há endpoint
    para editar um responsável depois de criado, por isso tem de ir na
    criação."""
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/responsaveis", headers=headers)
    responsavel_id = resp.json()[0]["id"]

    suf = sufixo_unico()
    resp = await client.post("/api/v1/responsaveis", headers=headers, json={
        "nome_completo": "Responsável Com Email", "telefone_contato": "+244911000000",
        "email": f"contacto.{suf}@teste.pt"
    })
    novo_responsavel_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/alunos/{dados['aluno_id']}/responsaveis", headers=headers, json={
        "responsavel_id": novo_responsavel_id, "tipo_parentesco": "Pai", "responsavel_financeiro": False
    })
    assert resp.status_code == 201, resp.text
    del responsavel_id  # só usado para confirmar que o vínculo original (sem e-mail) já existia
    return dados


async def test_comunicado_para_turma_resolve_emails_e_notifica_no_portal(client):
    escola = await criar_escola_e_gestor(client, "comunicados-turma")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_email_contacto(client, headers, ano_letivo)

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "Reunião de Pais", "corpo": "Reunião dia 10.",
        "destinatario_tipo": "TURMA", "destinatario_turma_id": dados["turma_id"]
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_destinatarios"] == 1

    resp = await client.get("/api/v1/comunicados", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1

    # Visível para a família no Portal, independentemente do envio de e-mail.
    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])
    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/comunicados", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    assert resp.json()[0]["titulo"] == "Reunião de Pais"


async def test_comunicado_sem_email_de_contacto_conta_zero_destinatarios(client):
    """Não é bug: ResponsavelFinanceiroLegal.email é opcional — se nunca
    for preenchido, o responsável simplesmente não recebe e-mail
    (mas o comunicado é criado à mesma e continua visível no Portal)."""
    escola = await criar_escola_e_gestor(client, "comunicados-sem-email")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "Sem e-mail", "corpo": "...",
        "destinatario_tipo": "TURMA", "destinatario_turma_id": dados["turma_id"]
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_destinatarios"] == 0


async def test_comunicado_para_aluno_so_conta_responsaveis_com_email(client):
    escola = await criar_escola_e_gestor(client, "comunicados-aluno")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_email_contacto(client, headers, date.today().year)

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "CONVOCATORIA", "titulo": "Convocatória Individual", "corpo": "...",
        "destinatario_tipo": "ALUNO", "destinatario_aluno_id": dados["aluno_id"]
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_destinatarios"] == 1


async def test_comunicado_toda_escola(client):
    escola = await criar_escola_e_gestor(client, "comunicados-escola")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    await _criar_aluno_matriculado_com_email_contacto(client, headers, ano_letivo)
    await _criar_aluno_matriculado_com_email_contacto(client, headers, ano_letivo)

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "Aviso Geral", "corpo": "...", "destinatario_tipo": "ESCOLA"
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_destinatarios"] == 2


async def test_professor_nao_pode_comunicar_com_toda_a_escola(client):
    escola = await criar_escola_e_gestor(client, "comunicados-rbac-escola")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, f"Prof. Comunica {sufixo_unico()}")

    resp = await client.post("/api/v1/comunicados", headers=auth_headers(token_professor), json={
        "tipo": "COMUNICADO", "titulo": "Não devia enviar", "corpo": "...", "destinatario_tipo": "ESCOLA"
    })
    assert resp.status_code == 403, resp.text
    assert "toda a escola" in resp.json()["detail"]


async def test_professor_so_comunica_com_turmas_onde_esta_alocado(client):
    escola = await criar_escola_e_gestor(client, "comunicados-rbac-turma")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, date.today().year)
    _, token_professor = await _criar_professor_com_token(client, headers, f"Prof. Fora {sufixo_unico()}")

    resp = await client.post("/api/v1/comunicados", headers=auth_headers(token_professor), json={
        "tipo": "COMUNICADO", "titulo": "Turma que não lecciona", "corpo": "...",
        "destinatario_tipo": "TURMA", "destinatario_turma_id": turma_id
    })
    assert resp.status_code == 403, resp.text


async def test_comunicado_destinatario_invalido_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "comunicados-destinatario-invalido")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "X", "corpo": "...", "destinatario_tipo": "PROFESSORES_TODOS"
    })
    assert resp.status_code == 400, resp.text


async def test_comunicado_turma_sem_destinatario_turma_id_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "comunicados-turma-sem-id")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "X", "corpo": "...", "destinatario_tipo": "TURMA"
    })
    assert resp.status_code == 400, resp.text
    assert "Selecione a turma" in resp.json()["detail"]


async def test_comunicados_isolados_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "comunicados-iso-a")
    escola_b = await criar_escola_e_gestor(client, "comunicados-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])

    await client.post("/api/v1/comunicados", headers=headers_a, json={
        "tipo": "COMUNICADO", "titulo": "Só da escola A", "corpo": "...", "destinatario_tipo": "ESCOLA"
    })

    resp = await client.get("/api/v1/comunicados", headers=headers_b)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0
