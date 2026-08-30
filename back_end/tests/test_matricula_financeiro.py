"""Fluxo de negócio principal: Curso -> Série -> Turma -> Aluno ->
Matrícula -> Contrato Financeiro -> Faturas geradas automaticamente.
É o caminho que, mais do que qualquer outro, uma escola real percorre
no primeiro dia de uso — se isto partir, a plataforma não serve para
nada, por mais módulos que tenha à volta."""
import io
from datetime import date, timedelta

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


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


async def _criar_aluno(client, headers, nome: str = "Aluno de Teste") -> str:
    resp = await client.post(
        "/api/v1/alunos",
        json={"matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-05-10"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ==========================================
# FIM DE CICLO + REINGRESSO (ver app/cruds/matriculas.py)
# ==========================================
async def test_fim_de_ciclo_exige_motivo_valido(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "fim-ciclo")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    matricula_id = resp.json()["id"]

    # Sem motivo — rejeitado.
    resp = await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers,
                               json={"status_matricula": "CICLO_CONCLUIDO"})
    assert resp.status_code == 400

    # Motivo fora da lista — rejeitado.
    resp = await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers,
                               json={"status_matricula": "CICLO_CONCLUIDO", "motivo": "FOI_DE_FERIAS"})
    assert resp.status_code == 400

    # Motivo válido — aceite e persistido.
    resp = await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers,
                               json={"status_matricula": "CICLO_CONCLUIDO", "motivo": "TRANSFERENCIA_EXTERNA"})
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers)
    historico = resp.json()
    assert historico[0]["status_matricula"] == "CICLO_CONCLUIDO"


async def test_reingresso_depois_de_fim_de_ciclo(client):
    """O aluno tem Fim de Ciclo (foi para uma escola fora da
    plataforma) e depois volta — o Reingresso é só uma nova matrícula
    normal, agora possivelmente noutra turma/ano; não há um endpoint
    separado, é o mesmo POST /matriculas de sempre."""
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "reingresso")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    matricula_id = resp.json()["id"]
    await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers,
                        json={"status_matricula": "CICLO_CONCLUIDO", "motivo": "TRANSFERENCIA_EXTERNA"})

    # Uma nova turma, ano seguinte — o Reingresso.
    turma_nova_id = await _preparar_turma_com_vaga(client, headers, ano_letivo + 1)
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_nova_id, "ano_letivo": ano_letivo + 1})
    assert resp.status_code == 201, resp.text
    assert resp.json()["status_matricula"] == "ATIVO"


# ==========================================
# DOCUMENTOS DA MATRÍCULA (sobretudo Reingresso "para outra classe")
# ==========================================
async def test_documento_matricula_upload_listar_ver_remover(client):
    ano_letivo = date.today().year
    escola = await criar_escola_e_gestor(client, "matricula-doc")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    aluno_id = await _criar_aluno(client, headers)
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    matricula_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/matriculas/{matricula_id}/documentos", headers=headers, params={"descricao": "Certificado da escola anterior"},
        files={"ficheiro": ("certificado.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    documentos = resp.json()["documentos"]
    assert len(documentos) == 1
    assert documentos[0]["descricao"] == "Certificado da escola anterior"
    doc_id = documentos[0]["id"]

    resp = await client.get(f"/api/v1/matriculas/{matricula_id}/documentos", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/matriculas/{matricula_id}/documentos/{doc_id}/url", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:image/png;base64,")

    resp = await client.delete(f"/api/v1/matriculas/{matricula_id}/documentos/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["documentos"] == []


async def test_documento_matricula_isolado_por_tenant(client):
    ano_letivo = date.today().year
    escola_a = await criar_escola_e_gestor(client, "matricula-doc-iso-a")
    escola_b = await criar_escola_e_gestor(client, "matricula-doc-iso-b")
    headers_a = auth_headers(escola_a["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers_a, ano_letivo)
    aluno_id = await _criar_aluno(client, headers_a)
    resp = await client.post("/api/v1/matriculas", headers=headers_a,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    matricula_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/matriculas/{matricula_id}/documentos", headers=auth_headers(escola_b["token"]),
        files={"ficheiro": ("x.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 404
