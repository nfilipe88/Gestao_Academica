"""Área do Encarregado — dashboard de estatísticas (aproveitamento +
assiduidade + comportamento), pedido self-service de transferência/
reingresso e histórico de comunicados. Ver app/cruds/portal.py."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def test_estatisticas_do_educando_calcula_media_e_assiduidade(client):
    escola = await criar_escola_e_gestor(client, "portal-dash-stats")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={"nome": "Matemática"})
    assert resp.status_code == 201, resp.text
    disciplina_id = resp.json()["id"]

    resp = await client.post("/api/v1/diario/periodos", headers=headers, json={"nome": "1º Trimestre"})
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/turmas/{dados['turma_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    resp = await client.post(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{disciplina_id}/notas/lote", headers=headers,
        json={"periodo_avaliacao": "1º Trimestre", "notas": [{"matricula_id": matricula_id, "valor_nota": "7.50"}]}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{disciplina_id}/frequencias/lote", headers=headers,
        json={
            "data_aula": str(date.today()), "quantidade_aulas": 4,
            "frequencias": [{"matricula_id": matricula_id, "presenca": False, "faltas": 1}]
        }
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(f"/api/v1/comportamento/turmas/{dados['turma_id']}/alunos/{dados['aluno_id']}", headers=headers, json={
        "tipo": "POSITIVO", "descricao": "Ajudou um colega."
    })
    assert resp.status_code == 201, resp.text
    resp = await client.post(f"/api/v1/comportamento/turmas/{dados['turma_id']}/alunos/{dados['aluno_id']}", headers=headers, json={
        "tipo": "NEGATIVO", "descricao": "Chegou atrasado."
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    token_responsavel = resp.json()["access_token"]

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/estatisticas", headers=auth_headers(token_responsavel))
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["media_geral"] == 7.5
    assert stats["media_por_disciplina"] == [{"disciplina_id": disciplina_id, "nome_disciplina": "Matemática", "media": 7.5, "quantidade_notas": 1}]
    assert stats["total_faltas"] == 1
    assert stats["total_aulas"] == 4
    assert stats["taxa_assiduidade"] == 75.0
    assert stats["comportamento"]["total_positivos"] == 1
    assert stats["comportamento"]["total_negativos"] == 1
    assert len(stats["comportamento"]["recentes"]) == 2


async def test_comunicados_do_educando_filtra_por_destinatario(client):
    escola = await criar_escola_e_gestor(client, "portal-dash-comunicados")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    # Turma diferente da do aluno — não deve aparecer.
    resp = await client.post("/api/v1/academico/cursos", headers=headers, json={"nome": "Curso Outro"})
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", headers=headers, json={"curso_id": curso_id, "nome": "Série Outra"})
    serie_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/turmas", headers=headers, json={
        "serie_ano_id": serie_id, "nome_codigo": "Turma Irrelevante", "ano_letivo": ano_letivo, "vagas_maximas": 10
    })
    outra_turma_id = resp.json()["id"]

    for corpo in (
        {"tipo": "COMUNICADO", "titulo": "Aviso Geral", "corpo": "...", "destinatario_tipo": "ESCOLA"},
        {"tipo": "COMUNICADO", "titulo": "Aviso Turma", "corpo": "...", "destinatario_tipo": "TURMA", "destinatario_turma_id": dados["turma_id"]},
        {"tipo": "COMUNICADO", "titulo": "Aviso Individual", "corpo": "...", "destinatario_tipo": "ALUNO", "destinatario_aluno_id": dados["aluno_id"]},
        {"tipo": "COMUNICADO", "titulo": "Aviso Irrelevante", "corpo": "...", "destinatario_tipo": "TURMA", "destinatario_turma_id": outra_turma_id},
    ):
        resp = await client.post("/api/v1/comunicados", headers=headers, json=corpo)
        assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    token_responsavel = resp.json()["access_token"]

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/comunicados", headers=auth_headers(token_responsavel))
    assert resp.status_code == 200, resp.text
    titulos = {c["titulo"] for c in resp.json()}
    assert titulos == {"Aviso Geral", "Aviso Turma", "Aviso Individual"}


async def test_pedir_transferencia_self_service_notifica_secretaria_origem(client):
    escola_a = await criar_escola_e_gestor(client, "portal-dash-transf-a")
    escola_b = await criar_escola_e_gestor(client, "portal-dash-transf-b")
    headers_a = auth_headers(escola_a["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers_a, ano_letivo)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    token_responsavel = resp.json()["access_token"]

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/pedir-transferencia", headers=auth_headers(token_responsavel),
        json={"nif_destino": escola_b["nif"], "motivo": "Mudança de área de residência"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PENDENTE"

    resp = await client.get("/api/v1/notificacoes", headers=headers_a)
    assert resp.status_code == 200, resp.text
    assert any("encarregado pediu" in n["titulo"].lower() for n in resp.json())

    resp = await client.get("/api/v1/transferencias/minhas", headers=headers_a)
    assert resp.status_code == 200, resp.text
    assert any(s["aluno_id"] == dados["aluno_id"] and s["status"] == "PENDENTE" for s in resp.json()["items"])
