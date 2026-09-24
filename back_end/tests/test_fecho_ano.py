"""Fecho do trimestre (pendências) e do ano letivo (resultado final do aluno) —
app/core/resultados.py e app/api/v1/fecho.py."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_estatisticas import _criar_aluno_matriculado, _criar_curso_serie_turma

ANO = date.today().year


async def _configurar(client, headers, **criterios):
    config = (await client.get("/api/v1/configuracoes", headers=headers)).json()
    for chave in ("tem_logotipo", "termos_aceites_em", "termos_versao"):
        config.pop(chave, None)
    config.update(criterios)
    resp = await client.put("/api/v1/configuracoes", headers=headers, json=config)
    assert resp.status_code == 200, resp.text


async def _nota(client, headers, turma, disciplina, matricula, periodo, valor):
    resp = await client.post(f"/api/v1/diario/turmas/{turma}/disciplinas/{disciplina}/notas/lote", headers=headers, json={
        "periodo_avaliacao": periodo, "data_avaliacao": str(date.today()), "notas": [{"matricula_id": matricula, "valor_nota": valor}]})
    assert resp.status_code == 200, resp.text


async def _cenario(client, prefixo):
    escola = await criar_escola_e_gestor(client, prefixo)
    headers = auth_headers(escola["token"])
    turma = await _criar_curso_serie_turma(client, headers, ANO, "Curso Fecho", f"10ª {sufixo_unico(4)}")
    disciplina = (await client.post("/api/v1/academico/disciplinas", headers=headers, json={"nome": f"Mat {sufixo_unico(4)}", "carga_horaria_total": 4})).json()["id"]
    periodos = {}
    for nome in ("1º Trimestre", "2º Trimestre"):
        periodos[nome] = (await client.post("/api/v1/diario/periodos", headers=headers, json={"nome": nome})).json()["id"]
    alunos = {n: await _criar_aluno_matriculado(client, headers, turma, ANO, n, 15) for n in ("Ana", "Bruno", "Carla")}
    return headers, turma, disciplina, periodos, alunos


async def test_pendencias_do_trimestre_listam_quem_ainda_nao_tem_nota(client):
    headers, turma, disciplina, periodos, alunos = await _cenario(client, "fecho-pendencias")
    await _nota(client, headers, turma, disciplina, alunos["Ana"]["matricula_id"], "1º Trimestre", "8")
    resp = await client.get(f"/api/v1/fecho/periodos/{periodos['1º Trimestre']}/pendencias", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["periodo"] == "1º Trimestre" and corpo["total_alunos_sem_nota"] == 2
    assert sorted(corpo["pendencias"][0]["alunos_sem_nota"]) == ["Bruno", "Carla"]
    assert (await client.get(f"/api/v1/fecho/periodos/00000000-0000-0000-0000-000000000000/pendencias", headers=headers)).status_code == 404


async def test_fecho_do_ano_calcula_aprova_reprova_e_deixa_incompletos_por_fechar(client):
    headers, turma, disciplina, periodos, alunos = await _cenario(client, "fecho-ano")
    await _configurar(client, headers, nota_minima_aprovacao=5)
    m = {n: a["matricula_id"] for n, a in alunos.items()}
    for periodo, notas in (("1º Trimestre", {"Ana": "8", "Bruno": "3", "Carla": "9"}), ("2º Trimestre", {"Ana": "9", "Bruno": "4"})):
        for nome, valor in notas.items():
            await _nota(client, headers, turma, disciplina, m[nome], periodo, valor)

    previa = (await client.get(f"/api/v1/fecho/ano/{ANO}/previa", headers=headers)).json()
    assert previa["pode_fechar"] is False and set(previa["periodos_abertos"]) == {"1º Trimestre", "2º Trimestre"}
    por_nome = {a["nome_completo"]: a for a in previa["alunos"]}
    assert por_nome["Ana"]["resultado"] == "APROVADO" and por_nome["Ana"]["disciplinas"][0]["m_final"] == 8.5
    assert por_nome["Bruno"]["resultado"] == "REPROVADO"
    assert por_nome["Carla"]["resultado"] == "INCOMPLETO" and por_nome["Carla"]["em_falta"]

    # sem trancar os períodos não fecha
    resp = await client.post(f"/api/v1/fecho/ano/{ANO}", headers=headers)
    assert resp.status_code == 400 and "Tranque" in resp.json()["detail"]

    for periodo_id in periodos.values():
        assert (await client.patch(f"/api/v1/diario/periodos/{periodo_id}/trancar", headers=headers)).status_code == 200

    resp = await client.post(f"/api/v1/fecho/ano/{ANO}", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["fechados"] == 2 and corpo["completo"] is False
    assert [i["aluno"] for i in corpo["incompletos"]] == ["Carla"]

    previa = (await client.get(f"/api/v1/fecho/ano/{ANO}/previa", headers=headers)).json()
    atual = {a["nome_completo"]: a["resultado_atual"] for a in previa["alunos"]}
    assert atual == {"Ana": "APROVADO", "Bruno": "REPROVADO", "Carla": None}

    # com resultados gravados, não se reabre um período sem reabrir o fecho
    resp = await client.patch(f"/api/v1/diario/periodos/{periodos['2º Trimestre']}/reabrir", headers=headers)
    assert resp.status_code == 400 and "fecho" in resp.json()["detail"].lower()

    assert (await client.post(f"/api/v1/fecho/ano/{ANO}/reabrir", headers=headers)).json()["reabertas"] == 2
    assert (await client.patch(f"/api/v1/diario/periodos/{periodos['2º Trimestre']}/reabrir", headers=headers)).status_code == 200


async def test_fecho_exige_nota_minima_e_limite_de_faltas_e_tolerancia_de_disciplinas(client):
    headers, turma, disciplina, periodos, alunos = await _cenario(client, "fecho-criterios")
    m = {n: a["matricula_id"] for n, a in alunos.items()}
    for periodo_id in periodos.values():
        await client.patch(f"/api/v1/diario/periodos/{periodo_id}/trancar", headers=headers)

    resp = await client.post(f"/api/v1/fecho/ano/{ANO}", headers=headers)
    assert resp.status_code == 400 and "nota mínima" in resp.json()["detail"]

    # períodos trancados não deixam lançar: reabrir, lançar, voltar a trancar
    for periodo_id in periodos.values():
        await client.patch(f"/api/v1/diario/periodos/{periodo_id}/reabrir", headers=headers)
    for periodo in periodos:
        for nome in ("Ana", "Bruno", "Carla"):
            await _nota(client, headers, turma, disciplina, m[nome], periodo, "3" if nome != "Ana" else "9")
    # Bruno falta a tudo, Ana e Carla vão a todas as aulas
    resp = await client.post(f"/api/v1/diario/turmas/{turma}/disciplinas/{disciplina}/frequencias/lote", headers=headers, json={
        "data_aula": str(date.today()), "quantidade_aulas": 1,
        "frequencias": [{"matricula_id": m["Ana"], "presenca": True, "faltas": 0},
                        {"matricula_id": m["Bruno"], "presenca": False, "faltas": 1},
                        {"matricula_id": m["Carla"], "presenca": True, "faltas": 0}]})
    assert resp.status_code == 201, resp.text
    for periodo_id in periodos.values():
        await client.patch(f"/api/v1/diario/periodos/{periodo_id}/trancar", headers=headers)

    await _configurar(client, headers, nota_minima_aprovacao=5, limite_faltas_percentagem=20, max_disciplinas_reprovadas=0)
    resultado = {a["nome_completo"]: a["resultado"] for a in (await client.get(f"/api/v1/fecho/ano/{ANO}/previa", headers=headers)).json()["alunos"]}
    assert resultado == {"Ana": "APROVADO", "Bruno": "REPROVADO_FALTAS", "Carla": "REPROVADO"}

    # com tolerância de 1 disciplina em atraso, a Carla (1 disciplina abaixo) transita
    await _configurar(client, headers, max_disciplinas_reprovadas=1)
    resultado = {a["nome_completo"]: a["resultado"] for a in (await client.get(f"/api/v1/fecho/ano/{ANO}/previa", headers=headers)).json()["alunos"]}
    assert resultado["Carla"] == "APROVADO" and resultado["Bruno"] == "REPROVADO_FALTAS"


async def test_so_o_gestor_fecha_o_ano_e_a_pauta_do_portal_mostra_o_resultado(client):
    headers, turma, disciplina, periodos, alunos = await _cenario(client, "fecho-perfis")
    await _configurar(client, headers, nota_minima_aprovacao=5)
    for periodo in periodos:
        await _nota(client, headers, turma, disciplina, alunos["Ana"]["matricula_id"], periodo, "9")
    for nome in ("Bruno", "Carla"):
        for periodo in periodos:
            await _nota(client, headers, turma, disciplina, alunos[nome]["matricula_id"], periodo, "9")
    for periodo_id in periodos.values():
        await client.patch(f"/api/v1/diario/periodos/{periodo_id}/trancar", headers=headers)

    # acesso de aluno + pauta
    email = f"ana.fecho.{sufixo_unico()}@teste.pt"
    assert (await client.post(f"/api/v1/alunos/{alunos['Ana']['aluno_id']}/criar-acesso", headers=headers,
                              json={"email": email, "palavra_passe": "SenhaTeste123!"})).status_code == 201
    login = (await client.post("/api/v1/auth/login", data={"username": email, "password": "SenhaTeste123!"})).json()
    headers_aluno = auth_headers(login["access_token"])
    assert (await client.post(f"/api/v1/fecho/ano/{ANO}", headers=headers_aluno)).status_code == 403

    assert (await client.post(f"/api/v1/fecho/ano/{ANO}", headers=headers)).json()["fechados"] == 3
    pauta = (await client.get(f"/api/v1/portal/educandos/{alunos['Ana']['aluno_id']}/pauta", headers=headers_aluno))
    assert pauta.status_code == 200, pauta.text
    assert pauta.json()["resultado_final"] == "APROVADO"
