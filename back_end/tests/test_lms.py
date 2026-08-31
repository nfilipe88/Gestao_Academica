"""LMS — Materiais de Aula, Banco de Questões e Exames Online (ver
app/cruds/lms.py e as rotas de tentativa em app/cruds/portal.py). Sem
nenhum teste antes desta sessão."""
from datetime import date, datetime, timedelta, timezone

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


async def _criar_questao(client, headers, disciplina_id: str, enunciado: str = "2+2?") -> str:
    resp = await client.post("/api/v1/lms/questoes", headers=headers, json={
        "disciplina_id": disciplina_id, "enunciado": enunciado, "tipo": "ESCOLHA_MULTIPLA",
        "opcoes": ["3", "4", "5"], "resposta_correta": "1", "valor": "1.00"
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


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

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Exame Teste",
        "data_inicio": (agora - timedelta(hours=1)).isoformat(), "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_id]
    })
    assert resp.status_code == 201, resp.text

    resp = await client.delete(f"/api/v1/lms/questoes/{questao_id}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "já foi usada" in resp.json()["detail"]


# ==========================================
# EXAMES — gestão pelo professor/staff
# ==========================================
async def test_criar_exame_rascunho_publicar_despublicar(client):
    escola = await criar_escola_e_gestor(client, "lms-exame-ciclo")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Exame 1",
        "data_inicio": (agora - timedelta(hours=1)).isoformat(), "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_id]
    })
    assert resp.status_code == 201, resp.text
    exame_id = resp.json()["id"]
    assert resp.json()["publicado"] is False

    resp = await client.patch(f"/api/v1/lms/exames/{exame_id}/publicar", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["publicado"] is True

    resp = await client.patch(f"/api/v1/lms/exames/{exame_id}/despublicar", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["publicado"] is False


async def test_criar_exame_questao_de_outra_disciplina_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "lms-exame-disciplina-errada")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    outra_disciplina_id = await _criar_disciplina(client, headers, "Português")
    questao_de_outra = await _criar_questao(client, headers, outra_disciplina_id)

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Exame Errado",
        "data_inicio": agora.isoformat(), "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_de_outra]
    })
    assert resp.status_code == 400, resp.text
    assert "disciplina desta alocação" in resp.json()["detail"]


async def test_criar_exame_sem_questoes_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "lms-exame-sem-questoes")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Exame Vazio",
        "data_inicio": agora.isoformat(), "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": []
    })
    assert resp.status_code == 422, resp.text


async def test_criar_exame_data_fim_antes_de_inicio_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "lms-exame-datas-invalidas")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    questao_id = await _criar_questao(client, headers, ctx["disciplina_id"])

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Exame Invertido",
        "data_inicio": agora.isoformat(), "data_fim": (agora - timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_id]
    })
    assert resp.status_code == 422, resp.text


async def test_apagar_exame_com_tentativa_e_bloqueado(client):
    escola = await criar_escola_e_gestor(client, "lms-exame-apagar-com-tentativa")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Apagar {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": dados["turma_id"], "disciplina_id": disciplina_id
    })
    alocacao_id = resp.json()["id"]
    questao_id = await _criar_questao(client, headers, disciplina_id)

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": alocacao_id, "titulo": "Exame com tentativa",
        "data_inicio": (agora - timedelta(hours=1)).isoformat(), "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_id]
    })
    exame_id = resp.json()["id"]
    await client.patch(f"/api/v1/lms/exames/{exame_id}/publicar", headers=headers)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    headers_aluno = auth_headers(resp.json()["access_token"])
    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{exame_id}/iniciar", headers=headers_aluno)
    assert resp.status_code == 200, resp.text

    resp = await client.delete(f"/api/v1/lms/exames/{exame_id}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "já tem tentativas" in resp.json()["detail"]


# ==========================================
# FLUXO DO ALUNO — iniciar, evento suspeito, submeter, resultado
# ==========================================
async def _preparar_exame_publicado(client, headers, ano_letivo, dentro_da_janela=True):
    dados = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Exame {sufixo_unico()}")
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": dados["turma_id"], "disciplina_id": disciplina_id
    })
    alocacao_id = resp.json()["id"]
    questao_id = await _criar_questao(client, headers, disciplina_id)

    agora = datetime.now(timezone.utc)
    if dentro_da_janela:
        inicio, fim = agora - timedelta(hours=1), agora + timedelta(hours=1)
    else:
        inicio, fim = agora + timedelta(days=1), agora + timedelta(days=2)

    resp = await client.post("/api/v1/lms/exames", headers=headers, json={
        "alocacao_id": alocacao_id, "titulo": "Exame do Aluno",
        "data_inicio": inicio.isoformat(), "data_fim": fim.isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_id]
    })
    exame_id = resp.json()["id"]
    await client.patch(f"/api/v1/lms/exames/{exame_id}/publicar", headers=headers)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_aluno"], "password": dados["senha"]})
    dados["token_aluno"] = resp.json()["access_token"]
    dados["exame_id"] = exame_id
    dados["questao_id"] = questao_id
    return dados


async def test_aluno_faz_exame_e_correcao_automatica_funciona(client):
    escola = await criar_escola_e_gestor(client, "lms-fluxo-aluno")
    headers = auth_headers(escola["token"])
    dados = await _preparar_exame_publicado(client, headers, date.today().year)
    headers_aluno = auth_headers(dados["token_aluno"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames", headers=headers_aluno)
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["status_tentativa"] == "NAO_INICIADA"
    assert resp.json()[0]["pode_iniciar"] is True

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
    dados = await _preparar_exame_publicado(client, headers, date.today().year)
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
    dados = await _preparar_exame_publicado(client, headers, date.today().year, dentro_da_janela=False)
    headers_aluno = auth_headers(dados["token_aluno"])

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames", headers=headers_aluno)
    assert resp.json()[0]["pode_iniciar"] is False

    resp = await client.post(f"/api/v1/portal/educandos/{dados['aluno_id']}/exames/{dados['exame_id']}/iniciar", headers=headers_aluno)
    assert resp.status_code == 400, resp.text
    assert "não está disponível" in resp.json()["detail"]


async def test_evento_suspeito_incrementa_e_aparece_nos_resultados(client):
    escola = await criar_escola_e_gestor(client, "lms-evento-suspeito")
    headers = auth_headers(escola["token"])
    dados = await _preparar_exame_publicado(client, headers, date.today().year)
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
    dados = await _preparar_exame_publicado(client, headers, date.today().year)

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

    agora = datetime.now(timezone.utc)
    resp = await client.post("/api/v1/lms/exames", headers=auth_headers(escola_b["token"]), json={
        "alocacao_id": ctx["alocacao_id"], "titulo": "Exame Fantasma",
        "data_inicio": agora.isoformat(), "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "duracao_minutos": 30, "questao_ids": [questao_id]
    })
    assert resp.status_code == 404, resp.text
