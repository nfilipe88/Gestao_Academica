"""Trabalhos / Tarefas (ver app/cruds/tarefas.py) — distinto do Diário
de Classe (RegistroNota): tem prazo de entrega e um status de entrega
por aluno (não só uma nota). Sem nenhum teste antes desta sessão."""
from datetime import date, timedelta

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _criar_disciplina(client, headers, nome: str = "Matemática") -> str:
    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={
        "nome": f"{nome} {sufixo_unico()}", "carga_horaria_total": 4
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _preparar_alocacao_com_aluno(client, headers, ano_letivo: int) -> dict:
    """Turma com um aluno matriculado + Disciplina + Professor + Alocação."""
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, token_professor = await _criar_professor_com_token(client, headers, f"Prof. Tarefas {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": turma_id, "disciplina_id": disciplina_id
    })
    assert resp.status_code == 201, resp.text
    alocacao_id = resp.json()["id"]

    suf = sufixo_unico()
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{suf}", "nome_completo": "Aluno Tarefa", "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    assert resp.status_code == 201, resp.text
    matricula_id = resp.json()["id"]

    return {
        "turma_id": turma_id, "disciplina_id": disciplina_id, "alocacao_id": alocacao_id,
        "aluno_id": aluno_id, "matricula_id": matricula_id,
        "professor_id": professor_id, "token_professor": token_professor,
    }


async def test_criar_tarefa_gera_avaliacao_pendente_para_cada_aluno(client):
    escola = await criar_escola_e_gestor(client, "tarefas-basico")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 1",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    assert resp.status_code == 201, resp.text
    tarefa_id = resp.json()["id"]
    # Nota: a resposta de criação sempre devolve pendentes=0 (valor por
    # omissão de _serializar_tarefa) mesmo já tendo sido geradas
    # avaliações PENDENTE por baixo — só a listagem (abaixo) calcula a
    # contagem real. Cobre o comportamento atual, não necessariamente
    # o desejável.
    assert resp.json()["pendentes"] == 0

    resp = await client.get(f"/api/v1/tarefas/{tarefa_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    avaliacoes = resp.json()["avaliacoes"]
    assert len(avaliacoes) == 1
    assert avaliacoes[0]["matricula_id"] == ctx["matricula_id"]
    assert avaliacoes[0]["status"] == "PENDENTE"


async def test_avaliar_tarefa_lote_atualiza_status_e_nota(client):
    escola = await criar_escola_e_gestor(client, "tarefas-avaliar")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 2",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    tarefa_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/tarefas/{tarefa_id}/avaliar", headers=headers, json={
        "avaliacoes": [{"matricula_id": ctx["matricula_id"], "status": "ENTREGUE", "nota": "8.5", "observacoes": "Bom"}]
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["mensagem"] == "Avaliação registada para 1 aluno(s)."

    resp = await client.get(
        f"/api/v1/tarefas/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    tarefas = resp.json()
    assert len(tarefas) == 1
    assert tarefas[0]["pendentes"] == 0, "já avaliada, não deve continuar a contar como por corrigir"

    resp = await client.get(f"/api/v1/tarefas/{tarefa_id}", headers=headers)
    avaliacao = resp.json()["avaliacoes"][0]
    assert avaliacao["status"] == "ENTREGUE"
    assert float(avaliacao["nota"]) == 8.5
    assert avaliacao["observacoes"] == "Bom"


async def test_avaliar_tarefa_nota_fora_do_intervalo_e_rejeitada(client):
    escola = await criar_escola_e_gestor(client, "tarefas-nota-invalida")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 3",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    tarefa_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/tarefas/{tarefa_id}/avaliar", headers=headers, json={
        "avaliacoes": [{"matricula_id": ctx["matricula_id"], "status": "ENTREGUE", "nota": "15.00"}]
    })
    assert resp.status_code == 400, resp.text
    assert "fora do intervalo" in resp.json()["detail"]


async def test_avaliar_tarefa_status_invalido_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "tarefas-status-invalido")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 4",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    tarefa_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/tarefas/{tarefa_id}/avaliar", headers=headers, json={
        "avaliacoes": [{"matricula_id": ctx["matricula_id"], "status": "PERDIDO"}]
    })
    assert resp.status_code == 400, resp.text
    assert "Status inválido" in resp.json()["detail"]


async def test_tarefa_valor_maximo_zero_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "tarefas-valor-zero")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 5",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "0"
    })
    assert resp.status_code == 422, resp.text


async def test_tarefa_professor_so_gere_a_propria_alocacao(client):
    """RN01: um professor sem alocação nesta turma/disciplina não pode
    criar nem avaliar tarefas nela, mesmo autenticado normalmente."""
    escola = await criar_escola_e_gestor(client, "tarefas-rn01")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)
    _, token_outro_professor = await _criar_professor_com_token(client, headers, f"Prof. Sem Alocação {sufixo_unico()}")
    headers_outro = auth_headers(token_outro_professor)

    resp = await client.post("/api/v1/tarefas", headers=headers_outro, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 6",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    assert resp.status_code == 403, resp.text

    resp = await client.get(
        f"/api/v1/tarefas/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}", headers=headers_outro
    )
    assert resp.status_code == 403, resp.text


async def test_tarefa_professor_alocado_pode_gerir(client):
    escola = await criar_escola_e_gestor(client, "tarefas-professor-alocado")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)
    headers_professor = auth_headers(ctx["token_professor"])

    resp = await client.post("/api/v1/tarefas", headers=headers_professor, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 7",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    assert resp.status_code == 201, resp.text


async def test_tarefa_periodo_trancado_bloqueia_avaliacao(client):
    """RN03: se a tarefa referenciar um período de avaliação já
    trancado pela secretaria, a avaliação fica bloqueada."""
    escola = await criar_escola_e_gestor(client, "tarefas-periodo-trancado")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    nome_periodo = f"Período Tarefas {sufixo_unico()}"
    resp = await client.post("/api/v1/diario/periodos", headers=headers, json={"nome": nome_periodo})
    assert resp.status_code == 201, resp.text
    periodo_id = resp.json()["id"]

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista 8",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00",
        "periodo_avaliacao": nome_periodo
    })
    tarefa_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/diario/periodos/{periodo_id}/trancar", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"/api/v1/tarefas/{tarefa_id}/avaliar", headers=headers, json={
        "avaliacoes": [{"matricula_id": ctx["matricula_id"], "status": "ENTREGUE", "nota": "9.00"}]
    })
    assert resp.status_code == 403, resp.text
    assert "trancado" in resp.json()["detail"]


async def test_tarefa_isolada_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "tarefas-iso-a")
    escola_b = await criar_escola_e_gestor(client, "tarefas-iso-b")
    headers_a = auth_headers(escola_a["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers_a, date.today().year)

    resp = await client.post("/api/v1/tarefas", headers=auth_headers(escola_b["token"]), json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Lista Fantasma",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    assert resp.status_code == 404, resp.text


async def test_tarefas_visiveis_no_portal_do_aluno(client):
    """GET /portal/educandos/{id}/tarefas — o mesmo caminho usado pela
    aba Trabalhos do Portal."""
    escola = await criar_escola_e_gestor(client, "tarefas-portal")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Portal {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": dados["turma_id"], "disciplina_id": disciplina_id
    })
    alocacao_id = resp.json()["id"]

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": alocacao_id, "titulo": "Lista Portal",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    token_responsavel = resp.json()["access_token"]

    resp = await client.get(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/tarefas", headers=auth_headers(token_responsavel)
    )
    assert resp.status_code == 200, resp.text
    tarefas = resp.json()
    assert len(tarefas) == 1
    assert tarefas[0]["titulo"] == "Lista Portal"
    assert tarefas[0]["status"] == "PENDENTE"
