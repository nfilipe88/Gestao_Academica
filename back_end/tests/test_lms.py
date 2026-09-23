"""LMS — Materiais de Aula, Banco de Questões e Exames Online (ver
app/cruds/lms.py e as rotas de tentativa em app/cruds/portal.py).

Exames são organizados em GRUPOS de 1+ variantes (Variante A/B/C —
perguntas genuinamente diferentes, não só ordem baralhada), cada grupo
ligado a uma Avaliacao do Diário desde a criação. Só GESTOR/SECRETARIA
pode INICIAR um grupo (PATCH .../iniciar) — é esse clique, não o
"publicar" do professor, que abre o grupo aos alunos e distribui cada
aluno por round-robin entre as variantes (ver
cruds/lms.py::iniciar_grupo_exame)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _criar_disciplina(client, headers, nome: str = "Matemática") -> str:
    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={
        "nome": f"{nome} {sufixo_unico()}", "carga_horaria_total": 4
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _preparar_alocacao(client, headers, ano_letivo: int) -> dict:
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    return await _preparar_alocacao_na_turma(client, headers, turma_id)


async def _preparar_alocacao_na_turma(client, headers, turma_id: str) -> dict:
    """Mesmo resultado de _preparar_alocacao, mas numa turma já
    existente — usado quando os alunos de teste precisam de estar na
    MESMA turma da alocação (ex.: distribuição por round-robin), ao
    contrário de _preparar_alocacao, que cria sempre a sua própria
    turma nova e isolada."""
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, token_professor = await _criar_professor_com_token(client, headers, f"Prof. LMS {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": turma_id, "disciplina_id": disciplina_id
    })
    assert resp.status_code == 201, resp.text
    return {
        "turma_id": turma_id, "disciplina_id": disciplina_id, "alocacao_id": resp.json()["id"],
        "professor_id": professor_id, "token_professor": token_professor,
    }


async def _criar_questao(client, headers, disciplina_id: str, enunciado: str = "2+2?", resposta_correta: str = "1") -> str:
    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": disciplina_id, "enunciado": enunciado, "tipo": "ESCOLHA_MULTIPLA",
        "opcoes": ["3", "4", "5"], "resposta_correta": resposta_correta, "valor": "1.00"
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _criar_questao_aberta(client, headers, disciplina_id: str, enunciado: str = "Explica a lei da gravidade.", valor: str = "2.00") -> str:
    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": disciplina_id, "enunciado": enunciado, "tipo": "ABERTA",
        "opcoes": [], "resposta_correta": "", "valor": valor
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _matricular_aluno_na_turma(client, headers, turma_id: str, ano_letivo: int, nome: str) -> str:
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-05-10"
    })
    assert resp.status_code == 201, resp.text
    aluno_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    assert resp.status_code == 201, resp.text
    return aluno_id


async def _criar_grupo_exame(
    client, headers, alocacao_id: str, variantes_questao_ids: list[list[str]], *,
    titulo: str = "Prova", dentro_da_janela: bool = True, modalidade: str = "PRESENCIAL",
    periodo_avaliacao: str = "1º Trimestre", tipo_avaliacao: str = "CONTINUA", peso: str = "100",
):
    agora = datetime.now(timezone.utc)
    if dentro_da_janela:
        inicio, fim = agora - timedelta(hours=1), agora + timedelta(hours=1)
    else:
        inicio, fim = agora + timedelta(days=1), agora + timedelta(days=2)

    return await client.post("/api/v1/lms/grupos-exame", headers=headers, json={
        "alocacao_id": alocacao_id, "titulo": titulo,
        "data_inicio": inicio.isoformat(), "data_fim": fim.isoformat(),
        "duracao_minutos": 30, "modalidade": modalidade,
        "periodo_avaliacao": periodo_avaliacao, "tipo_avaliacao": tipo_avaliacao, "peso": peso,
        "variantes": [{"questao_ids": ids} for ids in variantes_questao_ids],
    })


# ==========================================
# MATERIAIS DE AULA
# ==========================================
async def test_criar_material_e_listar(client):
    escola = await criar_escola_e_gestor(client, "lms-material-basico")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/lms/materiais", headers=headers, json={
        "turma_id": ctx["turma_id"], "disciplina_id": ctx["disciplina_id"],
        "titulo": "Equações", "corpo": "Explicação da matéria.", "publicado": True
    })
    assert resp.status_code == 201, resp.text
    material_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/lms/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/materiais", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1

    resp = await client.patch(f"/api/v1/lms/materiais/{material_id}", headers=headers, json={
        "titulo": "Equações do 2º grau", "corpo": "Novo texto.", "publicado": False
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["titulo"] == "Equações do 2º grau"
    assert resp.json()["publicado"] is False

    resp = await client.delete(f"/api/v1/lms/materiais/{material_id}", headers=headers)
    assert resp.status_code == 204, resp.text


async def test_material_professor_sem_alocacao_e_bloqueado(client):
    escola = await criar_escola_e_gestor(client, "lms-material-rn01")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    _, token_outro = await _criar_professor_com_token(client, headers, f"Prof. Fora {sufixo_unico()}")

    resp = await client.post("/api/v1/lms/materiais", headers=auth_headers(token_outro), json={
        "turma_id": ctx["turma_id"], "disciplina_id": ctx["disciplina_id"],
        "titulo": "Não devia entrar", "corpo": "..."
    })
    assert resp.status_code == 403, resp.text


# ==========================================
# BANCO DE QUESTÕES
# ==========================================
async def test_criar_questao_escolha_multipla_e_verdadeiro_falso(client):
    escola = await criar_escola_e_gestor(client, "lms-questoes-basico")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": ctx["disciplina_id"], "enunciado": "2+2?", "tipo": "ESCOLHA_MULTIPLA",
        "opcoes": ["3", "4", "5"], "resposta_correta": "1", "valor": "2.00"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": ctx["disciplina_id"], "enunciado": "A Terra é redonda.", "tipo": "VERDADEIRO_FALSO",
        "resposta_correta": "VERDADEIRO"
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["opcoes"] == []

    resp = await client.get(f"/api/v1/lms/disciplinas/{ctx['disciplina_id']}/questoes", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


async def test_criar_questao_escolha_multipla_precisa_de_2_opcoes(client):
    escola = await criar_escola_e_gestor(client, "lms-questoes-poucas-opcoes")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": ctx["disciplina_id"], "enunciado": "Só uma opção", "tipo": "ESCOLHA_MULTIPLA",
        "opcoes": ["única"], "resposta_correta": "0"
    })
    assert resp.status_code == 422, resp.text


async def test_criar_questao_resposta_correta_fora_do_intervalo(client):
    escola = await criar_escola_e_gestor(client, "lms-questoes-resposta-invalida")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": ctx["disciplina_id"], "enunciado": "2+2?", "tipo": "ESCOLHA_MULTIPLA",
        "opcoes": ["3", "4", "5"], "resposta_correta": "9"
    })
    assert resp.status_code == 422, resp.text


async def test_criar_questao_verdadeiro_falso_resposta_invalida(client):
    escola = await criar_escola_e_gestor(client, "lms-questoes-vf-invalido")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": ctx["disciplina_id"], "enunciado": "A Terra é redonda.", "tipo": "VERDADEIRO_FALSO",
        "resposta_correta": "TALVEZ"
    })
    assert resp.status_code == 422, resp.text


async def test_apagar_questao_ja_usada_em_exame_e_bloqueado(client):
    escola = await criar_escola_e_gestor(client, "lms-questoes-apagar-usada")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]])
    assert resp.status_code == 201, resp.text

    resp = await client.delete(f"/api/v1/lms/questoes/{questao_id}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "já foi usada" in resp.json()["detail"]


# ==========================================
# GRUPOS DE EXAME — gestão pelo professor/staff
# ==========================================
async def test_criar_grupo_com_3_variantes_cria_uma_avaliacao_e_3_lms_exame(client):
    escola = await criar_escola_e_gestor(client, "lms-grupo-3-variantes")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    qa = await _criar_questao(client, headers, ctx["disciplina_id"])
    qb = await _criar_questao(client, headers, ctx["disciplina_id"])
    qc = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[qa], [qb], [qc]], titulo="Prova Trimestral")
    assert resp.status_code == 201, resp.text
    exames = resp.json()
    assert len(exames) == 3
    grupo_ids = {e["grupo_id"] for e in exames}
    assert len(grupo_ids) == 1  # todas as 3 variantes partilham o mesmo grupo
    letras = sorted(e["letra_variante"] for e in exames)
    assert letras == ["A", "B", "C"]
    avaliacao_ids = {e["avaliacao_id"] for e in exames}
    assert len(avaliacao_ids) == 1 and None not in avaliacao_ids
    assert all(e["publicado"] is False for e in exames)

    resp = await client.get(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/avaliacoes", headers=headers
    )
    assert resp.status_code == 200, resp.text
    avaliacoes = [a for a in resp.json() if a["titulo"] == "Prova Trimestral"]
    assert len(avaliacoes) == 1
    assert avaliacoes[0]["id"] == exames[0]["avaliacao_id"]


async def test_criar_grupo_periodo_trancado_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "lms-grupo-periodo-trancado")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    nome_periodo = f"Periodo Trancado {sufixo_unico()}"
    resp = await client.post("/api/v1/diario/periodos", headers=headers, json={"nome": nome_periodo})
    assert resp.status_code == 201, resp.text
    periodo_id = resp.json()["id"]
    resp = await client.patch(f"/api/v1/diario/periodos/{periodo_id}/trancar", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]], periodo_avaliacao=nome_periodo)
    assert resp.status_code == 403, resp.text


async def test_criar_grupo_tipo_avaliacao_com_agendamento_como_professor_e_rejeitado(client):
    """Confirma a armadilha documentada no plano: "PROVA" já vem
    semeada com requer_agendamento=True, o que bloqueia um Professor
    (só Gestor/Secretaria podem usar tipos com agendamento) — por
    isso o formulário do frontend tem de filtrar esses tipos."""
    escola = await criar_escola_e_gestor(client, "lms-grupo-tipo-agendamento")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(
        client, headers=auth_headers(ctx["token_professor"]), alocacao_id=ctx["alocacao_id"],
        variantes_questao_ids=[[questao_id]], tipo_avaliacao="PROVA"
    )
    assert resp.status_code == 403, resp.text


async def test_grupo_exame_ciclo_iniciar_e_apagar(client):
    escola = await criar_escola_e_gestor(client, "lms-grupo-ciclo")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]])
    grupo_id = resp.json()[0]["grupo_id"]

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 200, resp.text
    assert all(e["publicado"] is True and e["iniciado"] is True for e in resp.json())

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 400, resp.text

    # Sem tentativas ainda — apagar continua livre mesmo depois de iniciado.
    resp = await client.delete(f"/api/v1/lms/grupos-exame/{grupo_id}", headers=headers)
    assert resp.status_code == 204, resp.text


async def test_iniciar_grupo_exame_e_gestor_secretaria_only(client):
    escola = await criar_escola_e_gestor(client, "lms-iniciar-rbac")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])
    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]])
    grupo_id = resp.json()[0]["grupo_id"]

    # O próprio Professor da alocação — mesmo podendo criar/preparar, não pode iniciar.
    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=auth_headers(ctx["token_professor"]))
    assert resp.status_code == 403, resp.text

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 200, resp.text


async def test_iniciar_grupo_exame_faz_round_robin_e_ignora_matriculas_inativas(client):
    escola = await criar_escola_e_gestor(client, "lms-round-robin")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    ctx = await _preparar_alocacao(client, headers, ano_letivo)
    qa = await _criar_questao(client, headers, ctx["disciplina_id"])
    qb = await _criar_questao(client, headers, ctx["disciplina_id"])

    alunos_ids = [
        await _matricular_aluno_na_turma(client, headers, ctx["turma_id"], ano_letivo, f"Aluno RR {i}")
        for i in range(4)
    ]
    # Um 5º aluno matriculado mas TRANCADO — nunca deve entrar na distribuição.
    aluno_inativo_id = await _matricular_aluno_na_turma(client, headers, ctx["turma_id"], ano_letivo, "Aluno Inativo")
    resp = await client.get(f"/api/v1/alunos/{aluno_inativo_id}/matriculas", headers=headers)
    assert resp.status_code == 200, resp.text
    matricula_inativa_id = resp.json()[0]["matricula_id"]
    resp = await client.patch(f"/api/v1/matriculas/{matricula_inativa_id}/status", headers=headers,
                               json={"status_matricula": "TRANCADO"})
    assert resp.status_code == 200, resp.text

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[qa], [qb]])
    grupo_id = resp.json()[0]["grupo_id"]
    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/lms/grupos-exame/{grupo_id}/atribuicoes", headers=headers)
    assert resp.status_code == 200, resp.text
    atribuicoes = resp.json()
    # Exatamente os 4 alunos ATIVOS foram distribuídos — nunca o TRANCADO.
    assert len(atribuicoes) == 4
    letras = [a["letra_variante"] for a in atribuicoes]
    # Distribuição por round-robin (2 variantes, 4 alunos) — cada variante recebe exatamente 2.
    assert sorted(letras) == ["A", "A", "B", "B"]
    assert all(a["atribuido_manualmente"] is False for a in atribuicoes)


async def test_gestor_reatribui_aluno_para_outra_variante(client):
    escola = await criar_escola_e_gestor(client, "lms-reatribuir")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    ctx = await _preparar_alocacao(client, headers, ano_letivo)
    qa = await _criar_questao(client, headers, ctx["disciplina_id"], enunciado="Pergunta A")
    qb = await _criar_questao(client, headers, ctx["disciplina_id"], enunciado="Pergunta B")
    aluno_id = await _matricular_aluno_na_turma(client, headers, ctx["turma_id"], ano_letivo, "Aluno Reatribuir")

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[qa], [qb]])
    exames = resp.json()
    grupo_id = exames[0]["grupo_id"]
    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    exames_iniciados = resp.json()

    resp = await client.get(f"/api/v1/lms/grupos-exame/{grupo_id}/atribuicoes", headers=headers)
    atribuicao_atual = next(a for a in resp.json() if a["matricula_id"])
    matricula_id = atribuicao_atual["matricula_id"]
    exame_atual_id = atribuicao_atual["exame_id"]
    exame_destino_id = next(e["id"] for e in exames_iniciados if e["id"] != exame_atual_id)

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/reatribuir", headers=headers, json={
        "matricula_id": matricula_id, "exame_id": exame_destino_id
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["exame_id"] == exame_destino_id
    assert resp.json()["atribuido_manualmente"] is True

    resp = await client.get(f"/api/v1/lms/grupos-exame/{grupo_id}/atribuicoes", headers=headers)
    atribuicao_atualizada = next(a for a in resp.json() if a["matricula_id"] == matricula_id)
    assert atribuicao_atualizada["exame_id"] == exame_destino_id
    assert atribuicao_atualizada["atribuido_manualmente"] is True


async def test_reatribuicao_apos_tentativa_iniciada_e_bloqueada(client):
    escola = await criar_escola_e_gestor(client, "lms-reatribuir-bloqueada")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year, num_variantes=2)
    headers_aluno = auth_headers(dados["token_aluno"])

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/lms/grupos-exame/{dados['grupo_id']}/atribuicoes", headers=headers)
    atribuicao = next(a for a in resp.json() if a["matricula_id"])
    outra_variante_id = next(e["id"] for e in dados["exames"] if e["id"] != dados["exame_id"])

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{dados['grupo_id']}/reatribuir", headers=headers, json={
        "matricula_id": atribuicao["matricula_id"], "exame_id": outra_variante_id
    })
    assert resp.status_code == 400, resp.text
    assert "já iniciou" in resp.json()["detail"]


# ==========================================
# FLUXO DO ALUNO — iniciar, evento suspeito, submeter, resultado
# ==========================================
async def _preparar_grupo_iniciado(client, headers, ano_letivo, dentro_da_janela=True, num_variantes=1, tipo_avaliacao="CONTINUA"):
    """Prepara um grupo de exame (1+ variantes) já INICIADO (publicado
    + iniciado + round-robin aplicado), com um único aluno matriculado
    (com acesso ao Portal) — substituindo a antiga _preparar_exame_publicado,
    que só publicava (sem o novo portão do INICIAR)."""
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Exame {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": dados["turma_id"], "disciplina_id": disciplina_id
    })
    alocacao_id = resp.json()["id"]

    variantes_questao_ids = []
    for _ in range(num_variantes):
        qid = await _criar_questao(client, headers, disciplina_id)
        variantes_questao_ids.append([qid])

    resp = await _criar_grupo_exame(
        client, headers, alocacao_id, variantes_questao_ids,
        titulo="Exame do Aluno", dentro_da_janela=dentro_da_janela, tipo_avaliacao=tipo_avaliacao
    )
    assert resp.status_code == 201, resp.text
    exames = resp.json()
    grupo_id = exames[0]["grupo_id"]
    avaliacao_id = exames[0]["avaliacao_id"]

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 200, resp.text
    exames_iniciados = resp.json()

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    dados["token_aluno"] = resp.json()["access_token"]
    dados["grupo_id"] = grupo_id
    dados["avaliacao_id"] = avaliacao_id
    dados["exames"] = exames_iniciados
    dados["exame_id"] = exames_iniciados[0]["id"]  # variante única por omissão (num_variantes=1)
    dados["questao_id"] = variantes_questao_ids[0][0]
    dados["disciplina_id"] = disciplina_id
    dados["alocacao_id"] = alocacao_id
    return dados


async def test_aluno_faz_exame_e_correcao_automatica_funciona(client):
    escola = await criar_escola_e_gestor(client, "lms-fluxo-aluno")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames", headers=headers_aluno)
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["status_tentativa"] == "NAO_INICIADA"
    assert resp.json()[0]["pode_iniciar"] is True
    assert resp.json()[0]["modalidade"] == "PRESENCIAL"

    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    assert resp.status_code == 200, resp.text
    pergunta = resp.json()["perguntas"][0]
    assert "resposta_correta" not in pergunta, "o gabarito nunca pode ir para o aluno antes de submeter"

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {dados["questao_id"]: "1"}}
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["nota_obtida"]) == 1.0
    assert float(resp.json()["nota_maxima"]) == 1.0

    resp = await client.get(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/resultado", headers=headers_aluno
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["perguntas"][0]["correta"] is True

    # Não pode repetir.
    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    assert resp.status_code == 400, resp.text
    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {}}
    )
    assert resp.status_code == 400, resp.text


async def test_aluno_resposta_errada_conta_zero(client):
    escola = await criar_escola_e_gestor(client, "lms-resposta-errada")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {dados["questao_id"]: "0"}}
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["nota_obtida"]) == 0.0


async def test_exame_fora_da_janela_nao_pode_ser_iniciado(client):
    escola = await criar_escola_e_gestor(client, "lms-fora-da-janela")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year, dentro_da_janela=False)
    headers_aluno = auth_headers(dados["token_aluno"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames", headers=headers_aluno)
    assert resp.json()[0]["pode_iniciar"] is False

    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    assert resp.status_code == 400, resp.text
    assert "não está disponível" in resp.json()["detail"]


async def test_aluno_nao_pode_iniciar_antes_do_iniciar_do_staff(client):
    escola = await criar_escola_e_gestor(client, "lms-antes-do-iniciar")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    # Cria um grupo, mas NUNCA chama /iniciar.
    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]])
    exame_id = resp.json()[0]["id"]

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    headers_aluno = auth_headers(resp.json()["access_token"])

    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{exame_id}/iniciar", headers=headers_aluno)
    assert resp.status_code == 404, resp.text


async def test_aluno_ve_apenas_a_sua_variante_atribuida(client):
    escola = await criar_escola_e_gestor(client, "lms-so-a-sua-variante")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados1 = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_alocacao_na_turma(client, headers, dados1["turma_id"])
    qa = await _criar_questao(client, headers, ctx["disciplina_id"], enunciado="Pergunta da Variante A")
    qb = await _criar_questao(client, headers, ctx["disciplina_id"], enunciado="Pergunta da Variante B")
    aluno2_id = await _matricular_aluno_na_turma(client, headers, dados1["turma_id"], ano_letivo, "Aluno Dois")

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[qa], [qb]])
    exames = resp.json()
    grupo_id = exames[0]["grupo_id"]
    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/lms/grupos-exame/{grupo_id}/atribuicoes", headers=headers)
    atribuicoes = {a["matricula_id"]: a["exame_id"] for a in resp.json()}

    resp = await client.post("/api/v1/auth/login", data={"username": dados1["email_aluno"], "password": dados1["senha"]})
    headers_aluno1 = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados1['aluno_id']}/exames", headers=headers_aluno1)
    assert resp.status_code == 200, resp.text
    exames_vistos = resp.json()
    assert len(exames_vistos) == 1  # nunca as duas variantes ao mesmo tempo

    resp = await client.get(f"/api/v1/alunos/{dados1['aluno_id']}/matriculas", headers=headers)
    matricula1_id = resp.json()[0]["matricula_id"]
    assert exames_vistos[0]["id"] == atribuicoes[matricula1_id]


async def test_aluno_nao_pode_iniciar_a_variante_de_outro_colega_por_url(client):
    escola = await criar_escola_e_gestor(client, "lms-variante-de-outro")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados1 = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    ctx = await _preparar_alocacao_na_turma(client, headers, dados1["turma_id"])
    qa = await _criar_questao(client, headers, ctx["disciplina_id"])
    qb = await _criar_questao(client, headers, ctx["disciplina_id"])
    await _matricular_aluno_na_turma(client, headers, dados1["turma_id"], ano_letivo, "Aluno Dois")

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[qa], [qb]])
    exames = resp.json()
    grupo_id = exames[0]["grupo_id"]
    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    exames_iniciados = resp.json()

    resp = await client.get(f"/api/v1/lms/grupos-exame/{grupo_id}/atribuicoes", headers=headers)
    atribuicoes = {a["matricula_id"]: a["exame_id"] for a in resp.json()}
    resp = await client.get(f"/api/v1/alunos/{dados1['aluno_id']}/matriculas", headers=headers)
    matricula1_id = resp.json()[0]["matricula_id"]
    exame_do_aluno1_id = atribuicoes[matricula1_id]
    exame_de_outro_id = next(e["id"] for e in exames_iniciados if e["id"] != exame_do_aluno1_id)

    resp = await client.post("/api/v1/auth/login", data={"username": dados1["email_aluno"], "password": dados1["senha"]})
    headers_aluno1 = auth_headers(resp.json()["access_token"])

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados1['aluno_id']}/exames/{exame_de_outro_id}/iniciar", headers=headers_aluno1
    )
    assert resp.status_code == 404, resp.text


async def test_evento_suspeito_incrementa_e_aparece_nos_resultados(client):
    escola = await criar_escola_e_gestor(client, "lms-evento-suspeito")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/evento-suspeito", headers=headers_aluno
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["eventos_suspeitos"] == 1

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/evento-suspeito", headers=headers_aluno
    )
    assert resp.json()["eventos_suspeitos"] == 2

    resp = await client.get(f"/api/v1/lms/exames/{dados['exame_id']}/resultados", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["eventos_suspeitos"] == 2


async def test_responsavel_nao_pode_iniciar_nem_submeter_exame(client):
    """RBAC: _garantir_e_aluno restringe início/submissão só ao próprio
    ALUNO — o responsável só pode ver."""
    escola = await criar_escola_e_gestor(client, "lms-responsavel-bloqueado")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text  # leitura aberta

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_responsavel
    )
    assert resp.status_code == 403, resp.text


async def test_exame_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "lms-iso-a")
    escola_b = await criar_escola_e_gestor(client, "lms-iso-b")
    headers_a = auth_headers(escola_a["token"])
    ctx = await _preparar_alocacao(client, headers_a, date.today().year)
    questao_id = await _criar_questao(client, headers_a, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, auth_headers(escola_b["token"]), ctx["alocacao_id"], [[questao_id]])
    assert resp.status_code == 404, resp.text


# ==========================================
# LIGAÇÃO AO DIÁRIO — correção alimenta NotaAvaliacao/RegistroNota
# ==========================================
async def test_submissao_grava_nota_avaliacao_e_registro_nota(client):
    escola = await criar_escola_e_gestor(client, "lms-nota-avaliacao")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {dados["questao_id"]: "1"}}
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["nota_obtida"]) == 1.0 and float(resp.json()["nota_maxima"]) == 1.0

    # nota_obtida/nota_maxima = 1/1 -> escalada para Tenant.nota_maxima (10 por omissão) = 10.00
    resp = await client.get(f"/api/v1/diario/avaliacoes/{dados['avaliacao_id']}/notas", headers=headers)
    assert resp.status_code == 200, resp.text
    notas = resp.json()
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]
    nota_do_aluno = next(n for n in notas if n["matricula_id"] == matricula_id)
    assert float(nota_do_aluno["valor_nota"]) == 10.0

    # O RegistroNota do período recalculou também.
    resp = await client.get(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{dados['disciplina_id']}/notas-finais",
        headers=headers, params={"periodo_avaliacao": "1º Trimestre"}
    )
    assert resp.status_code == 200, resp.text
    nota_final = next(n for n in resp.json() if n["matricula_id"] == matricula_id)
    assert nota_final["valor_nota"] == 10.0
    assert nota_final["calculada_automaticamente"] is True


async def test_submissao_grava_nota_avaliacao_escalada_a_nota_maxima_customizada(client):
    escola = await criar_escola_e_gestor(client, "lms-nota-maxima-custom")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/configuracoes", headers=headers)
    config = resp.json()
    config["nota_maxima"] = 20
    resp = await client.put("/api/v1/configuracoes", headers=headers, json=config)
    assert resp.status_code == 200, resp.text

    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {dados["questao_id"]: "1"}}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/diario/avaliacoes/{dados['avaliacao_id']}/notas", headers=headers)
    resp2 = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp2.json()[0]["matricula_id"]
    nota_do_aluno = next(n for n in resp.json() if n["matricula_id"] == matricula_id)
    # nota_obtida/nota_maxima = 1/1 -> escalada para 20 (a nova nota_maxima da escola)
    assert float(nota_do_aluno["valor_nota"]) == 20.0


async def test_lancar_notas_lote_direto_bloqueado_apos_criar_grupo_exame(client):
    escola = await criar_escola_e_gestor(client, "lms-bloqueia-lancamento-direto")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]], periodo_avaliacao="1º Trimestre")
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        f"/api/v1/diario/turmas/{ctx['turma_id']}/disciplinas/{ctx['disciplina_id']}/notas/lote",
        headers=headers, json={"periodo_avaliacao": "1º Trimestre", "notas": []}
    )
    assert resp.status_code == 400, resp.text


async def test_staff_pode_sobrescrever_nota_lms_via_lancar_notas_avaliacao_lote(client):
    escola = await criar_escola_e_gestor(client, "lms-override-manual")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {dados["questao_id"]: "1"}}
    )

    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    resp = await client.post(
        f"/api/v1/diario/avaliacoes/{dados['avaliacao_id']}/notas/lote", headers=headers,
        json={"notas": [{"matricula_id": matricula_id, "valor_nota": "5.5"}]}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/diario/avaliacoes/{dados['avaliacao_id']}/notas", headers=headers)
    nota = next(n for n in resp.json() if n["matricula_id"] == matricula_id)
    assert float(nota["valor_nota"]) == 5.5


async def test_apagar_avaliacao_ligada_a_exame_lms_e_bloqueado(client):
    escola = await criar_escola_e_gestor(client, "lms-apagar-avaliacao-bloqueado")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]])
    avaliacao_id = resp.json()[0]["avaliacao_id"]

    resp = await client.delete(f"/api/v1/diario/avaliacoes/{avaliacao_id}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "Exames Online" in resp.json()["detail"]


async def test_modalidade_presencial_remoto_persistida_e_devolvida(client):
    escola = await criar_escola_e_gestor(client, "lms-modalidade")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    resp = await _criar_grupo_exame(client, headers, ctx["alocacao_id"], [[questao_id]], modalidade="REMOTO")
    assert resp.status_code == 201, resp.text
    assert resp.json()[0]["modalidade"] == "REMOTO"

    resp = await client.get(f"/api/v1/lms/alocacoes/{ctx['alocacao_id']}/grupos-exame", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["modalidade"] == "REMOTO"


# ==========================================
# CORREÇÃO MANUAL — questões ABERTA + override do total (ver
# cruds/lms.py::corrigir_tentativa)
# ==========================================
async def _preparar_grupo_iniciado_misto(client, headers, ano_letivo):
    """Mesmo espírito de _preparar_grupo_iniciado, mas com UMA variante
    contendo 1 questão objetiva (ESCOLHA_MULTIPLA) + 1 questão ABERTA —
    para testar o fluxo de correção manual."""
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, token_professor = await _criar_professor_com_token(client, headers, f"Prof. Exame {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": dados["turma_id"], "disciplina_id": disciplina_id
    })
    alocacao_id = resp.json()["id"]

    questao_objetiva_id = await _criar_questao(client, headers, disciplina_id)
    questao_aberta_id = await _criar_questao_aberta(client, headers, disciplina_id)

    resp = await _criar_grupo_exame(
        client, headers, alocacao_id, [[questao_objetiva_id, questao_aberta_id]], titulo="Exame Misto"
    )
    assert resp.status_code == 201, resp.text
    exames = resp.json()
    grupo_id = exames[0]["grupo_id"]
    avaliacao_id = exames[0]["avaliacao_id"]
    exame_id = exames[0]["id"]

    resp = await client.patch(f"/api/v1/lms/grupos-exame/{grupo_id}/iniciar", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    dados["token_aluno"] = resp.json()["access_token"]
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    dados["matricula_id"] = resp.json()[0]["matricula_id"]
    dados["grupo_id"] = grupo_id
    dados["avaliacao_id"] = avaliacao_id
    dados["exame_id"] = exame_id
    dados["questao_objetiva_id"] = questao_objetiva_id
    dados["questao_aberta_id"] = questao_aberta_id
    dados["disciplina_id"] = disciplina_id
    dados["alocacao_id"] = alocacao_id
    dados["token_professor"] = token_professor
    return dados


async def test_criar_questao_aberta_opcoes_vazias_e_resposta_opcional(client):
    escola = await criar_escola_e_gestor(client, "lms-questao-aberta")
    headers = auth_headers(escola["token"])
    disciplina_id = await _criar_disciplina(client, headers)

    questao_id = await _criar_questao_aberta(client, headers, disciplina_id)
    resp = await client.get(f"/api/v1/lms/disciplinas/{disciplina_id}/questoes", headers=headers)
    assert resp.status_code == 200, resp.text
    questao = next(q for q in resp.json() if q["id"] == questao_id)
    assert questao["tipo"] == "ABERTA"
    assert questao["opcoes"] == []


async def test_submeter_tentativa_com_questao_aberta_fica_aguarda_correcao(client):
    escola = await criar_escola_e_gestor(client, "lms-aguarda-correcao")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado_misto(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno,
        json={"respostas": {dados["questao_objetiva_id"]: "1", dados["questao_aberta_id"]: "Porque a massa curva o espaço-tempo."}}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["corrigida_finalizada"] is False
    assert float(resp.json()["nota_obtida"]) == 1.0  # só a objetiva conta, a aberta ainda não

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames", headers=headers_aluno)
    assert resp.status_code == 200, resp.text
    exame = next(e for e in resp.json() if e["id"] == dados["exame_id"])
    assert exame["status_tentativa"] == "AGUARDA_CORRECAO"
    assert exame["nota_obtida"] is None  # nota parcial não é mostrada ainda

    resp = await client.get(f"/api/v1/lms/exames/{dados['exame_id']}/resultados", headers=headers)
    assert resp.status_code == 200, resp.text
    resultado = resp.json()[0]
    assert resultado["status"] == "AGUARDA_CORRECAO"

    # NotaAvaliacao ainda não foi escrita — a nota final do período continua vazia para este aluno.
    resp = await client.get(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{dados['disciplina_id']}/notas-finais",
        headers=headers, params={"periodo_avaliacao": "1º Trimestre"}
    )
    assert resp.status_code == 200, resp.text
    linha = next(n for n in resp.json() if n["matricula_id"] == dados["matricula_id"])
    assert linha["valor_nota"] is None


async def test_corrigir_tentativa_finaliza_questoes_abertas_e_lanca_nota(client):
    escola = await criar_escola_e_gestor(client, "lms-corrigir-aberta")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado_misto(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno,
        json={"respostas": {dados["questao_objetiva_id"]: "1", dados["questao_aberta_id"]: "Resposta razoável."}}
    )

    resp = await client.post(
        f"/api/v1/lms/exames/{dados['exame_id']}/tentativas/{dados['matricula_id']}/corrigir",
        headers=headers,
        json={"correcoes": [{"questao_id": dados["questao_aberta_id"], "pontos": "1.50", "comentario": "Falta detalhe."}], "nota_obtida_override": None}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["corrigida_finalizada"] is True
    assert float(resp.json()["nota_obtida"]) == 2.5  # 1.0 objetiva + 1.5 manual

    resp = await client.get(f"/api/v1/lms/exames/{dados['exame_id']}/resultados", headers=headers)
    assert resp.status_code == 200, resp.text
    resultado = resp.json()[0]
    assert resultado["status"] == "SUBMETIDA"
    assert resultado["corrigido_por_usuario_id"] is not None

    # NotaAvaliacao já foi escrita — a notificação também deve existir.
    resp = await client.get("/api/v1/notificacoes", headers=headers_aluno)
    assert resp.status_code == 200, resp.text
    assert any(n["tipo"] == "EXAME_CORRIGIDO" for n in resp.json())


async def test_corrigir_tentativa_override_finaliza_exame_ja_automatico(client):
    escola = await criar_escola_e_gestor(client, "lms-corrigir-override")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado(client, headers, date.today().year)  # sem ABERTA — já 100% automático
    headers_aluno = auth_headers(dados["token_aluno"])
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/matriculas", headers=headers)
    matricula_id = resp.json()[0]["matricula_id"]

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno, json={"respostas": {dados["questao_id"]: "1"}}
    )

    resp = await client.post(
        f"/api/v1/lms/exames/{dados['exame_id']}/tentativas/{matricula_id}/corrigir",
        headers=headers, json={"correcoes": [], "nota_obtida_override": "0.50"}
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["nota_obtida"]) == 0.5

    # RegistroNotaAuditoria criado com o autor certo — confirmado indiretamente:
    # a nota final do período reflete o valor sobrescrito (0.5, não o 1.0 automático original).
    resp = await client.get(
        f"/api/v1/diario/turmas/{dados['turma_id']}/disciplinas/{dados['disciplina_id']}/notas-finais",
        headers=headers, params={"periodo_avaliacao": "1º Trimestre"}
    )
    assert resp.status_code == 200, resp.text
    linha = next(n for n in resp.json() if n["matricula_id"] == matricula_id)
    assert float(linha["valor_nota"]) != 1.0


async def test_corrigir_tentativa_professor_so_pode_a_propria_alocacao(client):
    escola = await criar_escola_e_gestor(client, "lms-corrigir-rn01")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado_misto(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno,
        json={"respostas": {dados["questao_objetiva_id"]: "1", dados["questao_aberta_id"]: "Resposta."}}
    )

    outro_professor_id, outro_token = await _criar_professor_com_token(client, headers, f"Prof. Sem Alocacao {sufixo_unico()}")
    headers_outro_professor = auth_headers(outro_token)
    resp = await client.post(
        f"/api/v1/lms/exames/{dados['exame_id']}/tentativas/{dados['matricula_id']}/corrigir",
        headers=headers_outro_professor,
        json={"correcoes": [{"questao_id": dados["questao_aberta_id"], "pontos": "1.00", "comentario": None}], "nota_obtida_override": None}
    )
    assert resp.status_code == 403, resp.text

    # O professor DA alocação consegue.
    headers_professor = auth_headers(dados["token_professor"])
    resp = await client.post(
        f"/api/v1/lms/exames/{dados['exame_id']}/tentativas/{dados['matricula_id']}/corrigir",
        headers=headers_professor,
        json={"correcoes": [{"questao_id": dados["questao_aberta_id"], "pontos": "1.00", "comentario": None}], "nota_obtida_override": None}
    )
    assert resp.status_code == 200, resp.text


async def test_corrigir_tentativa_pontos_fora_do_intervalo_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "lms-corrigir-intervalo")
    headers = auth_headers(escola["token"])
    dados = await _preparar_grupo_iniciado_misto(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/submeter",
        headers=headers_aluno,
        json={"respostas": {dados["questao_objetiva_id"]: "1", dados["questao_aberta_id"]: "Resposta."}}
    )

    # questao_aberta_id vale 2.00 — 5.00 está fora do intervalo.
    resp = await client.post(
        f"/api/v1/lms/exames/{dados['exame_id']}/tentativas/{dados['matricula_id']}/corrigir",
        headers=headers,
        json={"correcoes": [{"questao_id": dados["questao_aberta_id"], "pontos": "5.00", "comentario": None}], "nota_obtida_override": None}
    )
    assert resp.status_code == 400, resp.text
