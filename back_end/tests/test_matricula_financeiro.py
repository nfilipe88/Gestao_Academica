"""Fluxo de negócio principal: Curso -> Série -> Turma -> Aluno ->
Matrícula -> Contrato Financeiro -> Faturas geradas automaticamente.
É o caminho que, mais do que qualquer outro, uma escola real percorre
no primeiro dia de uso — se isto partir, a plataforma não serve para
nada, por mais módulos que tenha à volta."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _preparar_turma_com_vaga(client, headers, ano_letivo: int) -> str:
    resp = await client.post("/api/v1/academico/cursos", json={"nome": "Ensino Secundário"}, headers=headers)
    assert resp.status_code == 201, resp.text
    curso_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/academico/series", json={"curso_id": curso_id, "nome": "10º Ano"}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    serie_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/academico/turmas",
        json={"serie_ano_id": serie_id, "nome_codigo": "10º A", "ano_letivo": ano_letivo, "vagas_maximas": 30},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_fluxo_completo_matricula_ate_faturas(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "fluxo")
    headers = auth_headers(escola["token"])

    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)

    suf = sufixo_unico()
    resp = await client.post(
        "/api/v1/alunos",
        json={
            "matricula_interna": f"AL{suf}",
            "nome_completo": "Aluno de Teste",
            "data_nascimento": "2012-05-10",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    aluno_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/responsaveis",
        json={"nome_completo": "Responsável de Teste", "telefone_contato": "+244900000000"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    responsavel_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/responsaveis",
        json={"responsavel_id": responsavel_id, "tipo_parentesco": "Mãe", "responsavel_financeiro": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        "/api/v1/matriculas",
        json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    matricula_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/financeiro/contratos",
        json={
            "matricula_id": matricula_id,
            "responsavel_id": responsavel_id,
            "valor_total_anual": "1200.00",
            "quantidade_parcelas": 12,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    contrato_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/financeiro/contratos/{contrato_id}/faturas", headers=headers)
    assert resp.status_code == 200, resp.text
    faturas = resp.json()

    assert len(faturas) == 12, f"esperava 12 parcelas geradas automaticamente, veio {len(faturas)}"
    soma = sum(float(f["valor_original"]) for f in faturas)
    assert abs(soma - 1200.00) < 0.05, f"a soma das parcelas ({soma}) devia ser ~1200.00"
    assert all(f["status_pagamento"] == "PENDENTE" for f in faturas)


async def test_matricula_duplicada_na_mesma_turma_e_recusada(client):
    """Um aluno não pode ficar matriculado duas vezes na mesma turma/ano —
    regra de negócio simples, mas se partir corrompe as contagens de
    vagas e a faturação duplica."""
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "dup")
    headers = auth_headers(escola["token"])

    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)

    suf = sufixo_unico()
    resp = await client.post(
        "/api/v1/alunos",
        json={"matricula_interna": f"AL{suf}", "nome_completo": "Aluno Duplicado", "data_nascimento": "2012-05-10"},
        headers=headers,
    )
    aluno_id = resp.json()["id"]

    corpo_matricula = {"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo}
    resp1 = await client.post("/api/v1/matriculas", json=corpo_matricula, headers=headers)
    assert resp1.status_code == 201, resp1.text

    resp2 = await client.post("/api/v1/matriculas", json=corpo_matricula, headers=headers)
    assert resp2.status_code >= 400, "uma segunda matrícula do mesmo aluno na mesma turma/ano devia ser recusada"
