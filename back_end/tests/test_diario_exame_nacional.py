"""Nota de Exame Nacional (NEN) — ver cruds/diario.py::lancar_nota_exame_nacional_lote
e models_diario.py::NotaExameNacional. Valor externo à escola, lançado
só por Gestor/Secretaria (nunca Professor), ligado à matrícula (não a
um período) — entra na Pauta do Portal como parte de M. Final."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga


async def _preparar_alocacao_com_aluno(client, headers, ano_letivo: int) -> dict:
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={
        "nome": f"Matemática {sufixo_unico()}", "carga_horaria_total": 4
    })
    assert resp.status_code == 201, resp.text
    disciplina_id = resp.json()["id"]

    professor_id, token_professor = await _criar_professor_com_token(client, headers, f"Prof. NEN {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": turma_id, "disciplina_id": disciplina_id
    })
    assert resp.status_code == 201, resp.text
    alocacao_id = resp.json()["id"]

    suf = sufixo_unico()
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{suf}", "nome_completo": "Aluno NEN", "data_nascimento": "2010-01-01"
    })
    assert resp.status_code == 201, resp.text
    aluno_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    assert resp.status_code == 201, resp.text
    matricula_id = resp.json()["id"]

    return {
        "turma_id": turma_id, "disciplina_id": disciplina_id, "alocacao_id": alocacao_id,
        "aluno_id": aluno_id, "matricula_id": matricula_id, "token_professor": token_professor,
    }


async def test_gestor_lanca_nen_com_sucesso(client):
    escola = await criar_escola_e_gestor(client, "nen-gestor-sucesso")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional/lote",
        headers=headers, json={"notas": [{"matricula_id": ctx["matricula_id"], "valor_nota": "7.50"}]}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1

    resp = await client.get(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional", headers=headers
    )
    assert resp.status_code == 200, resp.text
    linha = next(n for n in resp.json() if n["matricula_id"] == ctx["matricula_id"])
    assert linha["valor_nota"] == 7.5


async def test_professor_nao_pode_lancar_nen(client):
    escola = await criar_escola_e_gestor(client, "nen-professor-bloqueado")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)
    headers_professor = auth_headers(ctx["token_professor"])

    resp = await client.post(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional/lote",
        headers=headers_professor, json={"notas": [{"matricula_id": ctx["matricula_id"], "valor_nota": "7.50"}]}
    )
    assert resp.status_code == 403, resp.text

    # Leitura continua aberta ao Professor alocado.
    resp = await client.get(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional", headers=headers_professor
    )
    assert resp.status_code == 200, resp.text


async def test_lancar_nen_em_lote_faz_upsert(client):
    escola = await criar_escola_e_gestor(client, "nen-upsert")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional/lote",
        headers=headers, json={"notas": [{"matricula_id": ctx["matricula_id"], "valor_nota": "5.00"}]}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional/lote",
        headers=headers, json={"notas": [{"matricula_id": ctx["matricula_id"], "valor_nota": "9.00"}]}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional", headers=headers
    )
    assert resp.status_code == 200, resp.text
    linhas = [n for n in resp.json() if n["matricula_id"] == ctx["matricula_id"]]
    assert len(linhas) == 1
    assert linhas[0]["valor_nota"] == 9.0


async def test_listar_nen_da_turma_inclui_alunos_sem_nota(client):
    escola = await criar_escola_e_gestor(client, "nen-lista-sem-nota")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.get(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional", headers=headers
    )
    assert resp.status_code == 200, resp.text
    linha = next(n for n in resp.json() if n["matricula_id"] == ctx["matricula_id"])
    assert linha["valor_nota"] is None


async def test_lancar_nen_fora_do_intervalo_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "nen-fora-intervalo")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao_com_aluno(client, headers, date.today().year)

    resp = await client.post(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional/lote",
        headers=headers, json={"notas": [{"matricula_id": ctx["matricula_id"], "valor_nota": "99.00"}]}
    )
    assert resp.status_code == 400, resp.text
