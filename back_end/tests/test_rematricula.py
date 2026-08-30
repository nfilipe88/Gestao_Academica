"""Rematrícula — ecrã dedicado (Secretaria/Gestor) e rematrícula
self-service (Portal do encarregado). Ver app/cruds/matriculas.py::
listar_candidatos_rematricula e app/cruds/portal.py::pedir_rematricula.

Reaproveita RN05 (bloqueio por mensalidade em atraso de ano anterior,
já testado em test_matricula_financeiro.py) — aqui o que se testa é
que o mesmo bloqueio fica visível ANTES de tentar (no ecrã e no
self-service), não uma cópia da regra."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_portal_alertas_propina import _login, _preparar_aluno_com_fatura_em_atraso


async def _criar_aluno_matriculado_com_portal(client, headers, ano_letivo: int) -> dict:
    """Aluno + Responsável (ambos com acesso ao Portal), matriculados
    num ano letivo — SEM contrato financeiro nenhum, portanto nunca
    bloqueado por RN05. Usado nos cenários "caminho feliz" (candidato
    elegível, pedido de rematrícula aceite)."""
    suf = sufixo_unico()
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)

    email_aluno = f"aluno.rematricula.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{suf}", "nome_completo": "Aluno Rematrícula", "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/alunos/{aluno_id}/criar-acesso", headers=headers,
                              json={"email": email_aluno, "palavra_passe": senha})
    assert resp.status_code == 201, resp.text

    email_responsavel = f"responsavel.rematricula.{suf}@teste.pt"
    resp = await client.post("/api/v1/responsaveis", headers=headers,
                              json={"nome_completo": "Responsável Rematrícula", "telefone_contato": "+244900000000"})
    responsavel_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/responsaveis/{responsavel_id}/criar-acesso", headers=headers,
                              json={"email": email_responsavel, "palavra_passe": senha})
    assert resp.status_code == 201, resp.text
    await client.post(f"/api/v1/alunos/{aluno_id}/responsaveis", headers=headers,
                       json={"responsavel_id": responsavel_id, "tipo_parentesco": "Mãe", "responsavel_financeiro": True})

    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    assert resp.status_code == 201, resp.text

    return {
        "aluno_id": aluno_id, "turma_id": turma_id,
        "email_aluno": email_aluno, "email_responsavel": email_responsavel, "senha": senha,
    }


async def test_candidatos_rematricula_marca_bloqueado_por_atraso(client):
    escola = await criar_escola_e_gestor(client, "rematricula-bloqueado")
    headers = auth_headers(escola["token"])
    dados = await _preparar_aluno_com_fatura_em_atraso(client, headers)
    ano_letivo = date.today().year

    resp = await client.get(f"/api/v1/matriculas/rematricula-candidatos?ano_letivo={ano_letivo}", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["ano_letivo_origem"] == ano_letivo
    assert corpo["ano_letivo_destino"] == ano_letivo + 1
    candidato = next(c for c in corpo["candidatos"] if c["aluno_id"] == dados["aluno_id"])
    assert candidato["bloqueado_por_atraso"] is True
    assert candidato["pedido_confirmado_pela_familia"] is False


async def test_candidato_desaparece_da_lista_depois_de_renovado(client):
    escola = await criar_escola_e_gestor(client, "rematricula-renovar")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.get(f"/api/v1/matriculas/rematricula-candidatos?ano_letivo={ano_letivo}", headers=headers)
    candidato = next(c for c in resp.json()["candidatos"] if c["aluno_id"] == dados["aluno_id"])
    assert candidato["bloqueado_por_atraso"] is False

    # Renovar é só a mesma POST /matriculas de sempre, para o ano seguinte
    # (o ecrã de Rematrícula não introduz nenhuma rota nova para isto).
    turma_seguinte_id = await _preparar_turma_com_vaga(client, headers, ano_letivo + 1)
    resp = await client.post("/api/v1/matriculas", headers=headers, json={
        "aluno_id": dados["aluno_id"], "turma_id": turma_seguinte_id, "ano_letivo": ano_letivo + 1
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/matriculas/rematricula-candidatos?ano_letivo={ano_letivo}", headers=headers)
    assert not any(c["aluno_id"] == dados["aluno_id"] for c in resp.json()["candidatos"])


async def test_pedir_rematricula_self_service_notifica_secretaria(client):
    escola = await criar_escola_e_gestor(client, "rematricula-self-service")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    token_responsavel = await _login(client, dados["email_responsavel"], dados["senha"])
    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/pedir-rematricula",
                              headers=auth_headers(token_responsavel))
    assert resp.status_code == 200, resp.text
    assert resp.json()["pedido_rematricula_confirmado"] is True

    # O Gestor (que fez o registo da escola) recebe a notificação.
    resp = await client.get("/api/v1/notificacoes", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(n["tipo"] == "REMATRICULA" for n in resp.json())

    # O ecrã de Rematrícula reflete "família confirmou".
    resp = await client.get(f"/api/v1/matriculas/rematricula-candidatos?ano_letivo={ano_letivo}", headers=headers)
    candidato = next(c for c in resp.json()["candidatos"] if c["aluno_id"] == dados["aluno_id"])
    assert candidato["pedido_confirmado_pela_familia"] is True

    # E o próprio Portal (GET /meus-educandos) também já não oferece o botão.
    resp = await client.get("/api/v1/portal/meus-educandos", headers=auth_headers(token_responsavel))
    educando = resp.json()[0]
    assert educando["pedido_rematricula_confirmado"] is True

    # Idempotente: pedir uma segunda vez não falha nem duplica.
    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/pedir-rematricula",
                              headers=auth_headers(token_responsavel))
    assert resp.status_code == 200, resp.text


async def test_pedir_rematricula_bloqueado_por_atraso(client):
    escola = await criar_escola_e_gestor(client, "rematricula-self-service-bloq")
    headers = auth_headers(escola["token"])
    dados = await _preparar_aluno_com_fatura_em_atraso(client, headers)

    token_responsavel = await _login(client, dados["email_responsavel"], dados["senha"])
    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/pedir-rematricula",
                              headers=auth_headers(token_responsavel))
    assert resp.status_code == 403, resp.text


async def test_candidatos_rematricula_bloqueado_para_professor(client):
    """_PODE_GERIR em api/v1/matriculas.py é GESTOR + SECRETARIA só —
    o ecrã de Rematrícula é operação de secretaria, não do dia-a-dia
    do Professor na turma."""
    escola = await criar_escola_e_gestor(client, "rematricula-rbac-professor")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Rematrícula")

    resp = await client.get("/api/v1/matriculas/rematricula-candidatos", headers=auth_headers(token_professor))
    assert resp.status_code == 403, resp.text


async def test_candidatos_rematricula_ano_sem_matriculas_devolve_lista_vazia(client):
    """Um ano_letivo sem nenhuma matrícula ATIVO (ex.: escola acabada
    de criar) não deve rebentar — devolve a lista vazia, não erro."""
    escola = await criar_escola_e_gestor(client, "rematricula-ano-vazio")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/matriculas/rematricula-candidatos?ano_letivo=1999", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["ano_letivo_origem"] == 1999
    assert corpo["candidatos"] == []
