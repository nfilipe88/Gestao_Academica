"""Registos de Comportamento — ver app/cruds/comportamento.py. Mesma
autoria do Diário de Classe (Gestor/Secretaria sempre; Professor só
nas turmas onde lecciona), com a particularidade de um Professor só
poder remover os registos que ele próprio criou."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_matricula_financeiro import _preparar_turma_com_vaga


async def _matricular_aluno(client, headers, turma_id: str, ano_letivo: int, nome: str = "Aluno Comportamento") -> str:
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    assert resp.status_code == 201, resp.text
    return aluno_id


async def _criar_professor_com_token(client, headers, nome: str) -> tuple[str, str]:
    suf = sufixo_unico()
    email = f"prof.comportamento.{suf}@teste.pt"
    resp = await client.post("/api/v1/professores", headers=headers, json={
        "nome_completo": nome, "email": email, "palavra_passe": "SenhaTeste123!"
    })
    assert resp.status_code == 201, resp.text
    professor_id = resp.json()["id"]
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "SenhaTeste123!"})
    return professor_id, resp.json()["access_token"]


async def test_registar_e_listar_comportamento(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "comportamento-crud")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _matricular_aluno(client, headers, turma_id, ano_letivo)

    resp = await client.post(f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=headers, json={
        "tipo": "POSITIVO", "descricao": "Ajudou um colega com dificuldades."
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post(f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=headers, json={
        "tipo": "NEGATIVO", "descricao": "Chegou atrasado à aula."
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    registos = resp.json()
    assert len(registos) == 2
    assert {r["tipo"] for r in registos} == {"POSITIVO", "NEGATIVO"}
    assert all(r["registrado_por_nome"] == "Gestor comportamento-crud" for r in registos)


async def test_comportamento_rejeita_tipo_invalido(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "comportamento-tipo-invalido")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _matricular_aluno(client, headers, turma_id, ano_letivo)

    resp = await client.post(f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=headers, json={
        "tipo": "NEUTRO", "descricao": "..."
    })
    assert resp.status_code == 400


async def test_comportamento_rejeita_descricao_vazia(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "comportamento-descricao-vazia")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _matricular_aluno(client, headers, turma_id, ano_letivo)

    resp = await client.post(f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=headers, json={
        "tipo": "POSITIVO", "descricao": "   "
    })
    assert resp.status_code == 400, resp.text


async def test_professor_so_regista_em_turmas_onde_lecciona(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "comportamento-prof")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _matricular_aluno(client, headers, turma_id, ano_letivo)

    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={"nome": "Educação Física"})
    disciplina_id = resp.json()["id"]

    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Sem Alocação")

    resp = await client.post(
        f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=auth_headers(token_professor),
        json={"tipo": "POSITIVO", "descricao": "Participação exemplar."}
    )
    assert resp.status_code == 403, resp.text

    professor_id, token_professor2 = await _criar_professor_com_token(client, headers, "Prof. Alocado")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_id, "disciplina_id": disciplina_id})
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=auth_headers(token_professor2),
        json={"tipo": "POSITIVO", "descricao": "Participação exemplar."}
    )
    assert resp.status_code == 201, resp.text


async def test_professor_so_remove_os_seus_proprios_registos(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "comportamento-remover")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _matricular_aluno(client, headers, turma_id, ano_letivo)

    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={"nome": "História"})
    disciplina_id = resp.json()["id"]

    professor1_id, token1 = await _criar_professor_com_token(client, headers, "Professor Um")
    professor2_id, token2 = await _criar_professor_com_token(client, headers, "Professor Dois")
    for prof_id in (professor1_id, professor2_id):
        resp = await client.post(f"/api/v1/professores/{prof_id}/alocacoes", headers=headers,
                                  json={"turma_id": turma_id, "disciplina_id": disciplina_id})
        assert resp.status_code == 201, resp.text

    resp = await client.post(
        f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=auth_headers(token1),
        json={"tipo": "NEGATIVO", "descricao": "Não trouxe o material."}
    )
    registo_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/comportamento/registos/{registo_id}", headers=auth_headers(token2))
    assert resp.status_code == 403, resp.text

    resp = await client.delete(f"/api/v1/comportamento/registos/{registo_id}", headers=headers)
    assert resp.status_code == 200, resp.text


async def test_comportamento_isolado_por_tenant(client):
    ano_letivo = date.today().year
    escola_a = await criar_escola_e_gestor(client, "comportamento-iso-a")
    escola_b = await criar_escola_e_gestor(client, "comportamento-iso-b")
    headers_a = auth_headers(escola_a["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers_a, ano_letivo)
    aluno_id = await _matricular_aluno(client, headers_a, turma_id, ano_letivo)

    resp = await client.post(
        f"/api/v1/comportamento/turmas/{turma_id}/alunos/{aluno_id}", headers=auth_headers(escola_b["token"]),
        json={"tipo": "POSITIVO", "descricao": "..."}
    )
    assert resp.status_code == 404
