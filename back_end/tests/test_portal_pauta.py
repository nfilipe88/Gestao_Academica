"""Pauta unificada do educando (ver cruds/portal.py::obter_pauta_do_educando)
— a par do Boletim já existente (test_portal_dashboard.py cobre as
Estatísticas), com o detalhe por avaliação/período que o Boletim não
tem: cada avaliação individual (Diário) com a data de lançamento, a
média já calculada de cada período, e a Média Final por disciplina.

Também cobre o histórico de Anos Letivos (ano_letivo opcional) e a
estrutura MININED (MACT/PT, Faltas do Trimestre, MFD/MEO/NEN/M. Final)
acrescentados numa sessão seguinte — ver cruds/diario.py para NEN e
a janela data_inicio/data_fim de PeriodoAvaliacao."""
from datetime import date, timedelta

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _preparar_disciplina_alocada(client, headers, turma_id: str) -> dict:
    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={
        "nome": f"Física {sufixo_unico()}", "carga_horaria_total": 4
    })
    assert resp.status_code == 201, resp.text
    disciplina_id = resp.json()["id"]

    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Pauta {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": turma_id, "disciplina_id": disciplina_id
    })
    assert resp.status_code == 201, resp.text
    return {"disciplina_id": disciplina_id, "professor_id": professor_id, "alocacao_id": resp.json()["id"]}


async def _lancar_nota_avaliacao(client, headers, turma_id: str, disciplina_id: str, matricula_id: str, periodo: str, titulo: str, valor: str) -> None:
    resp = await client.post(
        f"/api/v1/diario/turmas/{turma_id}/disciplinas/{disciplina_id}/avaliacoes", headers=headers,
        json={"periodo_avaliacao": periodo, "titulo": titulo, "tipo_avaliacao": "CONTINUA", "peso": "100"}
    )
    assert resp.status_code == 201, resp.text
    avaliacao_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/diario/avaliacoes/{avaliacao_id}/notas/lote", headers=headers,
        json={"notas": [{"matricula_id": matricula_id, "valor_nota": valor}]}
    )
    assert resp.status_code == 200, resp.text


async def test_pauta_periodos_ordenados_por_data_nao_alfabetico(client):
    """"9º Trimestre" lançado antes de "10º Trimestre" tem de aparecer
    primeiro na Pauta — alfabeticamente seria o contrário ("10º" < "9º"),
    o mesmo bug que o Boletim (ordenado por string) já tinha."""
    escola = await criar_escola_e_gestor(client, "pauta-ordem-periodos")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "9º Trimestre", "Prova 9", "10.00")
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "10º Trimestre", "Prova 10", "8.00")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    nomes_periodos = [p["periodo_avaliacao"] for p in disciplina["periodos"]]
    assert nomes_periodos == ["9º Trimestre", "10º Trimestre"]


async def test_pauta_media_final_igual_a_estatisticas_media_por_disciplina(client):
    escola = await criar_escola_e_gestor(client, "pauta-media-final")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "10.00")
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "2º Trimestre", "Prova 2", "6.00")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina_pauta = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/estatisticas", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina_stats = next(d for d in resp.json()["media_por_disciplina"] if d["disciplina_id"] == ctx["disciplina_id"])

    assert disciplina_pauta["media_final"] == disciplina_stats["media"] == 8.0


async def test_pauta_trabalhos_nao_entram_no_calculo_da_media(client):
    escola = await criar_escola_e_gestor(client, "pauta-trabalhos-fora-da-media")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "10.00")

    resp = await client.post("/api/v1/tarefas", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Trabalho de Casa",
        "data_entrega": str(date.today() + timedelta(days=7)), "valor_maximo": "10.00"
    })
    assert resp.status_code == 201, resp.text
    tarefa_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/tarefas/{tarefa_id}/avaliar", headers=headers, json={
        "avaliacoes": [{"matricula_id": matricula_id, "status": "ENTREGUE", "nota": "0.00", "observacoes": None}]
    })
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    assert disciplina["media_final"] == 10.0, "a nota 0.00 do Trabalho não pode puxar a média para baixo"
    assert len(disciplina["trabalhos"]) == 1
    assert disciplina["trabalhos"][0]["nota"] == 0.0


async def test_pauta_tooltip_datas_presentes(client):
    escola = await criar_escola_e_gestor(client, "pauta-datas")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "9.00")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    periodo = disciplina["periodos"][0]
    assert periodo["avaliacoes"][0]["data_lancamento"] is not None
    assert periodo["media_data_atualizacao"] is not None


# ==========================================
# Histórico de Anos Letivos (ver cruds/portal.py::_obter_matricula_do_ano)
# ==========================================
async def test_pauta_ano_letivo_omitido_usa_matricula_atual(client):
    escola = await criar_escola_e_gestor(client, "pauta-ano-omitido")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    assert resp.json()["ano_letivo_selecionado"] == ano_letivo
    assert ano_letivo in resp.json()["anos_letivos_disponiveis"]


async def test_pauta_ano_letivo_explicito_devolve_ano_anterior(client):
    escola = await criar_escola_e_gestor(client, "pauta-ano-anterior")
    headers = auth_headers(escola["token"])
    ano_atual = date.today().year
    ano_anterior = ano_atual - 1
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_anterior)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id_anterior = resp.json()[0]["matricula_id"]
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id_anterior, "1º Trimestre", "Prova Ano Anterior", "7.00")

    # Segunda matrícula do MESMO aluno, no ano corrente, noutra turma —
    # mesmo mecanismo já usado pela Rematrícula.
    turma_atual_id = await _preparar_turma_com_vaga(client, headers, ano_atual)
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": dados["aluno_id"], "turma_id": turma_atual_id, "ano_letivo": ano_atual})
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    # Sem ano_letivo -> ano corrente (sem notas lançadas lá).
    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    assert resp.json()["ano_letivo_selecionado"] == ano_atual
    assert resp.json()["disciplinas"] == []

    # Com ano_letivo=ano_anterior -> mostra a disciplina lançada nesse ano.
    resp = await client.get(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel,
        params={"ano_letivo": ano_anterior}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ano_letivo_selecionado"] == ano_anterior
    assert any(d["disciplina_id"] == ctx["disciplina_id"] for d in resp.json()["disciplinas"])
    assert sorted(resp.json()["anos_letivos_disponiveis"], reverse=True) == resp.json()["anos_letivos_disponiveis"]
    assert set(resp.json()["anos_letivos_disponiveis"]) == {ano_atual, ano_anterior}


async def test_pauta_ano_letivo_sem_matricula_devolve_disciplinas_vazias(client):
    escola = await criar_escola_e_gestor(client, "pauta-ano-sem-matricula")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel,
        params={"ano_letivo": ano_letivo - 5}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["disciplinas"] == []
    assert resp.json()["ano_letivo_selecionado"] == ano_letivo - 5


# ==========================================
# MACT/PT estruturados (ver PautaTabelaComponent no frontend — aqui só
# se confirma a forma dos dados que o backend devolve).
# ==========================================
async def test_pauta_mact_pt_aparecem_distintos(client):
    escola = await criar_escola_e_gestor(client, "pauta-mact-pt")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    # MACT/PT não vêm semeados por omissão (só CONTINUA/PROVA) — só
    # existem depois de uma Importação de mini-pauta ou, como aqui, de o
    # Gestor os criar à mão em Configurações.
    for tipo in ("MACT", "PT"):
        resp = await client.post("/api/v1/configuracoes/tipos-avaliacao", headers=headers, json={"nome": tipo})
        assert resp.status_code == 201, resp.text

    for tipo, valor in (("MACT", "8.00"), ("PT", "6.00")):
        resp = await client.post(
            f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{ctx['disciplina_id']}/avaliacoes", headers=headers,
            json={"periodo_avaliacao": "1º Trimestre", "titulo": tipo, "tipo_avaliacao": tipo, "peso": "50"}
        )
        assert resp.status_code == 201, resp.text
        resp = await client.post(
            f"/api/v1/diario/avaliacoes/{resp.json()['id']}/notas/lote", headers=headers,
            json={"notas": [{"matricula_id": matricula_id, "valor_nota": valor}]}
        )
        assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    tipos = {a["tipo_avaliacao"] for a in disciplina["periodos"][0]["avaliacoes"]}
    assert tipos == {"MACT", "PT"}
    assert disciplina["periodos"][0]["media_periodo"] == 7.0  # (8*50 + 6*50) / 100


# ==========================================
# Faltas do trimestre (ver cruds/portal.py::_faltas_do_periodo e o novo
# PeriodoAvaliacao.data_inicio/data_fim).
# ==========================================
async def test_pauta_faltas_periodo_com_janela_configurada(client):
    escola = await criar_escola_e_gestor(client, "pauta-faltas-com-janela")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "9.00")

    resp = await client.post("/api/v1/diario/periodos", headers=headers, json={
        "nome": "1º Trimestre", "data_inicio": "2026-01-01", "data_fim": "2026-06-30"
    })
    assert resp.status_code == 201, resp.text

    # Falta DENTRO da janela — conta.
    resp = await client.post(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{ctx['disciplina_id']}/frequencias/lote", headers=headers,
        json={"data_aula": "2026-03-10", "quantidade_aulas": 1, "frequencias": [{"matricula_id": matricula_id, "presenca": False, "faltas": 1}]}
    )
    assert resp.status_code == 201, resp.text
    # Falta FORA da janela — não deve contar.
    resp = await client.post(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{ctx['disciplina_id']}/frequencias/lote", headers=headers,
        json={"data_aula": "2026-08-01", "quantidade_aulas": 1, "frequencias": [{"matricula_id": matricula_id, "presenca": False, "faltas": 1}]}
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])
    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    assert disciplina["periodos"][0]["faltas_periodo"] == 1


async def test_pauta_faltas_periodo_ausente_sem_janela_configurada(client):
    escola = await criar_escola_e_gestor(client, "pauta-faltas-sem-janela")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "9.00")
    # Sem criar nenhum PeriodoAvaliacao com data_inicio/data_fim.

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])
    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    assert disciplina["periodos"][0]["faltas_periodo"] is None


# ==========================================
# MFD/MEO/NEN/M. Final (ver cruds/diario.py para NEN)
# ==========================================
async def test_pauta_meo_igual_a_mfd(client):
    escola = await criar_escola_e_gestor(client, "pauta-meo-mfd")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "9.00")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])
    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    assert disciplina["media_exame_oral"] == disciplina["media_final"] == 9.0
    assert disciplina["m_final"] == 9.0  # sem NEN, cai para o MFD
    assert disciplina["nota_exame_nacional"] is None


async def test_pauta_m_final_usa_media_meo_nen_com_nen_lancada(client):
    escola = await criar_escola_e_gestor(client, "pauta-m-final-com-nen")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_disciplina_alocada(client, headers, dados["turma_id"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]
    await _lancar_nota_avaliacao(client, headers, dados["turma_id"], ctx["disciplina_id"], matricula_id, "1º Trimestre", "Prova 1", "8.00")

    resp = await client.post(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{ctx['disciplina_id']}/exame-nacional/lote", headers=headers,
        json={"notas": [{"matricula_id": matricula_id, "valor_nota": "6.00"}]}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])
    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/pauta", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    disciplina = next(d for d in resp.json()["disciplinas"] if d["disciplina_id"] == ctx["disciplina_id"])
    assert disciplina["nota_exame_nacional"] == 6.0
    assert disciplina["media_final"] == 8.0
    assert disciplina["m_final"] == 7.0  # (8 + 6) / 2


# ==========================================
# PATCH /diario/periodos/{id}/janela (ver cruds/diario.py::atualizar_janela_periodo_avaliacao)
# ==========================================
async def test_atualizar_janela_periodo_com_sucesso(client):
    escola = await criar_escola_e_gestor(client, "periodo-janela-sucesso")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/diario/periodos", headers=headers, json={"nome": "1º Trimestre"})
    assert resp.status_code == 201, resp.text
    periodo_id = resp.json()["id"]
    assert resp.json()["data_inicio"] is None and resp.json()["data_fim"] is None

    resp = await client.patch(f"/api/v1/diario/periodos/{periodo_id}/janela", headers=headers, json={
        "data_inicio": "2026-01-01", "data_fim": "2026-06-30"
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["data_inicio"] == "2026-01-01"
    assert resp.json()["data_fim"] == "2026-06-30"

    resp = await client.get("/api/v1/diario/periodos", headers=headers)
    periodo = next(p for p in resp.json() if p["id"] == periodo_id)
    assert periodo["data_inicio"] == "2026-01-01" and periodo["data_fim"] == "2026-06-30"


async def test_atualizar_janela_periodo_inicio_depois_de_fim_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "periodo-janela-invalida")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/diario/periodos", headers=headers, json={"nome": "1º Trimestre"})
    periodo_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/diario/periodos/{periodo_id}/janela", headers=headers, json={
        "data_inicio": "2026-06-30", "data_fim": "2026-01-01"
    })
    assert resp.status_code == 400, resp.text
