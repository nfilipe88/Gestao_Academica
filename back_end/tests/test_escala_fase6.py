"""
Fase 6 (escala): cobertura para o lançamento de frequência em lote
(cruds/diario.py::lancar_frequencias_lote) — a função foi reescrita
para deixar de fazer um SELECT por aluno dentro do loop (N+1) a favor
de uma única query prévia, e não havia nenhum teste automatizado sobre
ela antes desta fase. Prova o essencial: cria os registos certos, e um
relançamento do mesmo dia faz upsert (atualiza, não duplica).
"""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _preparar_turma_com_2_alunos(client, headers) -> dict:
    resp = await client.post("/api/v1/academico/cursos", json={"nome": "Ensino Primário"}, headers=headers)
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", json={"curso_id": curso_id, "nome": "1ª Classe"}, headers=headers)
    serie_id = resp.json()["id"]
    ano_letivo = date.today().year
    resp = await client.post(
        "/api/v1/academico/turmas",
        json={"serie_ano_id": serie_id, "nome_codigo": "1A", "ano_letivo": ano_letivo, "vagas_maximas": 30},
        headers=headers,
    )
    turma_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/disciplinas", json={"nome": "Matemática"}, headers=headers)
    disciplina_id = resp.json()["id"]

    matricula_ids = []
    for i in range(2):
        suf = sufixo_unico()
        resp = await client.post(
            "/api/v1/alunos",
            json={"matricula_interna": f"AL{suf}", "nome_completo": f"Aluno Frequência {i}", "data_nascimento": "2015-01-01"},
            headers=headers,
        )
        aluno_id = resp.json()["id"]
        resp = await client.post(
            "/api/v1/matriculas", json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo}, headers=headers
        )
        matricula_ids.append(resp.json()["id"])

    return {"turma_id": turma_id, "disciplina_id": disciplina_id, "matricula_ids": matricula_ids}


async def test_lancar_frequencias_lote_cria_e_depois_faz_upsert_sem_duplicar(client):
    gestor = await criar_escola_e_gestor(client, "freq")
    headers = auth_headers(gestor["token"])
    turma = await _preparar_turma_com_2_alunos(client, headers)
    m1, m2 = turma["matricula_ids"]

    corpo_url = f"/api/v1/diario/turmas/{turma['turma_id']}/disciplinas/{turma['disciplina_id']}/frequencias/lote"
    hoje = date.today().isoformat()

    resp = await client.post(corpo_url, headers=headers, json={
        "data_aula": hoje, "quantidade_aulas": 2, "conteudo_programado": "Frações",
        "frequencias": [
            {"matricula_id": m1, "presenca": True, "faltas": 0},
            {"matricula_id": m2, "presenca": False, "faltas": 2},
        ],
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["total"] == 2

    consolidado_url = f"/api/v1/diario/turmas/{turma['turma_id']}/disciplinas/{turma['disciplina_id']}/consolidado"
    consolidado = (await client.get(consolidado_url, headers=headers)).json()
    assert consolidado["total_faltas"] == 2  # 0 (m1) + 2 (m2)

    # Relançar o MESMO dia com valores diferentes tem de ATUALIZAR os
    # dois registos já existentes, não criar mais nenhum — se tivesse
    # duplicado (o bug que o N+1 antigo não causava, mas um upsert mal
    # feito causaria), o total seria 0+2+1+0=3, não 1.
    resp = await client.post(corpo_url, headers=headers, json={
        "data_aula": hoje, "quantidade_aulas": 2, "conteudo_programado": "Frações (revisão)",
        "frequencias": [
            {"matricula_id": m1, "presenca": False, "faltas": 1},
            {"matricula_id": m2, "presenca": True, "faltas": 0},
        ],
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["total"] == 2

    consolidado = (await client.get(consolidado_url, headers=headers)).json()
    assert consolidado["total_faltas"] == 1  # 1 (m1) + 0 (m2) — atualizado, não somado ao anterior


async def test_lancar_frequencias_lote_rejeita_matricula_de_outra_turma(client):
    gestor = await criar_escola_e_gestor(client, "freq-outra-turma")
    headers = auth_headers(gestor["token"])
    turma = await _preparar_turma_com_2_alunos(client, headers)

    resp = await client.post(
        f"/api/v1/diario/turmas/{turma['turma_id']}/disciplinas/{turma['disciplina_id']}/frequencias/lote",
        headers=headers,
        json={
            "data_aula": date.today().isoformat(), "quantidade_aulas": 1,
            "frequencias": [{"matricula_id": "00000000-0000-0000-0000-000000000000", "presenca": True, "faltas": 0}],
        },
    )
    assert resp.status_code == 400
