"""Calendário do ano letivo e abrir/encerrar matrículas e rematrículas
(app/api/v1/calendario.py e PATCH /configuracoes/inscricoes)."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_portal_alertas_propina import _login
from tests.test_rematricula import _criar_aluno_matriculado_com_portal

ANO = date.today().year


def _entrada(tipo="EXAMES", nome="Exames do 1º trimestre", ini=f"{ANO}-12-01", fim=f"{ANO}-12-12", **extra):
    return {"ano_letivo": ANO, "tipo": tipo, "nome": nome, "data_inicio": ini, "data_fim": fim, **extra}


async def test_calendario_crud_com_todos_os_tipos_e_validacoes(client):
    escola = await criar_escola_e_gestor(client, "calendario-crud")
    headers = auth_headers(escola["token"])

    tipos = ["PERIODO_LETIVO", "AVALIACOES", "EXAMES", "EXAMES_FINAIS", "EXAMES_RECURSO", "OUTRO"]
    for i, tipo in enumerate(tipos):
        resp = await client.post("/api/v1/calendario", headers=headers,
                                 json=_entrada(tipo, f"Marco {tipo}", f"{ANO}-{i + 1:02d}-01", f"{ANO}-{i + 1:02d}-10"))
        assert resp.status_code == 201, resp.text
    lista = (await client.get(f"/api/v1/calendario?ano_letivo={ANO}", headers=headers)).json()
    assert [i["tipo"] for i in lista] == tipos, "ordenado por data de início"

    assert (await client.post("/api/v1/calendario", headers=headers, json=_entrada(ini=f"{ANO}-12-20", fim=f"{ANO}-12-01"))).status_code == 422
    assert (await client.post("/api/v1/calendario", headers=headers, json=_entrada(tipo="INVENTADO"))).status_code == 422

    entrada_id = lista[2]["id"]
    resp = await client.patch(f"/api/v1/calendario/{entrada_id}", headers=headers, json={"nome": "Exames (alterado)", "data_fim": f"{ANO}-03-20"})
    assert resp.status_code == 200 and resp.json()["nome"] == "Exames (alterado)"
    assert (await client.patch(f"/api/v1/calendario/{entrada_id}", headers=headers, json={"data_inicio": f"{ANO}-06-01"})).status_code == 400

    assert (await client.delete(f"/api/v1/calendario/{entrada_id}", headers=headers)).status_code == 204
    assert len((await client.get(f"/api/v1/calendario?ano_letivo={ANO}", headers=headers)).json()) == 5
    assert (await client.get(f"/api/v1/calendario?ano_letivo={ANO + 1}", headers=headers)).json() == []


async def test_calendario_junta_os_trimestres_do_diario_e_estado_face_a_hoje(client):
    escola = await criar_escola_e_gestor(client, "calendario-diario")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/diario/periodos", headers=headers,
                             json={"nome": "1º Trimestre", "data_inicio": f"{ANO}-01-01", "data_fim": f"{ANO}-01-31"})
    assert resp.status_code == 201, resp.text
    await client.post("/api/v1/calendario", headers=headers, json=_entrada("EXAMES", "Exames em curso", f"{ANO}-01-01", f"{ANO + 1}-12-31"))

    lista = (await client.get(f"/api/v1/calendario?ano_letivo={ANO}", headers=headers)).json()
    diario = next(i for i in lista if i["origem"] == "DIARIO")
    assert diario["nome"] == "1º Trimestre" and diario["id"] is None
    assert next(i for i in lista if i["nome"] == "Exames em curso")["estado"] == "DECORRER"

    # se o calendário já tem um PERIODO_LETIVO com o mesmo nome, não duplica
    await client.post("/api/v1/calendario", headers=headers, json=_entrada("PERIODO_LETIVO", "1º Trimestre", f"{ANO}-01-01", f"{ANO}-01-31"))
    lista = (await client.get(f"/api/v1/calendario?ano_letivo={ANO}", headers=headers)).json()
    assert [i["origem"] for i in lista if i["nome"] == "1º Trimestre"] == ["CALENDARIO"]


async def test_calendario_isolado_por_escola_e_so_o_gestor_edita(client):
    escola = await criar_escola_e_gestor(client, "calendario-rbac")
    outra = await criar_escola_e_gestor(client, "calendario-rbac-outra")
    headers = auth_headers(escola["token"])
    entrada_id = (await client.post("/api/v1/calendario", headers=headers, json=_entrada())).json()["id"]

    assert (await client.get(f"/api/v1/calendario?ano_letivo={ANO}", headers=auth_headers(outra["token"]))).json() == []
    assert (await client.patch(f"/api/v1/calendario/{entrada_id}", headers=auth_headers(outra["token"]), json={"nome": "x" * 5})).status_code == 404
    assert (await client.delete(f"/api/v1/calendario/{entrada_id}", headers=auth_headers(outra["token"]))).status_code == 404

    dados = await _criar_aluno_matriculado_com_portal(client, headers, ANO)
    token_aluno = await _login(client, dados["email_aluno"], dados["senha"])
    assert (await client.get(f"/api/v1/calendario?ano_letivo={ANO}", headers=auth_headers(token_aluno))).status_code == 200
    assert (await client.post("/api/v1/calendario", headers=auth_headers(token_aluno), json=_entrada())).status_code == 403


async def test_rematriculas_encerradas_escondem_o_pedido_e_recusam_no_portal(client):
    escola = await criar_escola_e_gestor(client, "inscricoes-remat")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ANO)
    token = await _login(client, dados["email_responsavel"], dados["senha"])

    config = (await client.get("/api/v1/configuracoes", headers=headers)).json()
    assert config["matriculas_abertas"] is True and config["rematriculas_abertas"] is True

    resp = await client.patch("/api/v1/configuracoes/inscricoes", headers=headers, json={"rematriculas_abertas": False})
    assert resp.status_code == 200 and resp.json()["rematriculas_abertas"] is False and resp.json()["matriculas_abertas"] is True

    educando = (await client.get("/api/v1/portal/meus-educandos", headers=auth_headers(token))).json()[0]
    assert educando["rematriculas_abertas"] is False
    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/pedir-rematricula", headers=auth_headers(token))
    assert resp.status_code == 403 and "encerradas" in resp.json()["detail"]

    # a Secretaria/Gestor continua a poder renovar: o ecrã de Rematrícula não fecha
    assert (await client.get(f"/api/v1/matriculas/rematricula-candidatos?ano_letivo={ANO}", headers=headers)).status_code == 200

    await client.patch("/api/v1/configuracoes/inscricoes", headers=headers, json={"rematriculas_abertas": True})
    assert (await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/pedir-rematricula", headers=auth_headers(token))).status_code == 200


async def test_matriculas_encerradas_recusam_candidatura_mas_nao_o_contacto_rapido(client):
    escola = await criar_escola_e_gestor(client, "inscricoes-matricula")
    headers = auth_headers(escola["token"])
    await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={"ativo": True})
    candidatura = {"nome_responsavel": "Pai", "nome_aluno_candidato": "Filho", "email_contato": f"pai.{sufixo_unico()}@teste.pt",
                   "aceitou_regulamento": True, "candidatura_matricula": True}
    contacto = {"nome_responsavel": "Mãe", "nome_aluno_candidato": "Filha", "email_contato": f"mae.{sufixo_unico()}@teste.pt"}
    url = f"/api/v1/public/{escola['tenant_id']}/leads"

    assert (await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")).json()["matriculas_abertas"] is True
    assert (await client.post(url, json=candidatura)).status_code == 201

    assert (await client.patch("/api/v1/configuracoes/inscricoes", headers=headers, json={"matriculas_abertas": False})).status_code == 200
    assert (await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")).json()["matriculas_abertas"] is False
    resp = await client.post(url, json=candidatura)
    assert resp.status_code == 403 and "encerradas" in resp.json()["detail"]
    assert (await client.post(url, json=contacto)).status_code == 201, "o contacto rápido continua aberto"

    # a Secretaria/Gestor continua a poder matricular (POST /matriculas não é afetado)
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ANO)
    assert dados["aluno_id"]


async def test_so_o_gestor_abre_e_encerra_inscricoes(client):
    escola = await criar_escola_e_gestor(client, "inscricoes-perfil")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ANO)
    token_aluno = await _login(client, dados["email_aluno"], dados["senha"])
    resp = await client.patch("/api/v1/configuracoes/inscricoes", headers=auth_headers(token_aluno), json={"matriculas_abertas": False})
    assert resp.status_code == 403
