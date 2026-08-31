"""Grade horária (Horários) — ver app/cruds/horarios.py. Não tinha
nenhum teste antes desta sessão; foi a lacuna que deixou passar um bug
real: o listener de auditoria geral (app/core/auditoria.py) não sabia
serializar colunas `Time` (datetime.time) para o JSONB do audit_log,
rebentando o commit de QUALQUER criação de HorarioAula com um
"Object of type time is not JSON serializable" disfarçado de "Já
existe exatamente este slot" (o crud converte qualquer falha do
commit nessa mensagem — ver criar_horario)."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga


async def _criar_disciplina(client, headers, nome: str = "Matemática") -> str:
    resp = await client.post("/api/v1/academico/disciplinas", headers=headers, json={
        "nome": f"{nome} {sufixo_unico()}", "carga_horaria_total": 4
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _preparar_alocacao(client, headers, ano_letivo: int) -> dict:
    """Turma + Disciplina + Professor + Alocação — o mínimo para poder
    criar um slot na grade horária."""
    turma_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Horário {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers, json={
        "turma_id": turma_id, "disciplina_id": disciplina_id
    })
    assert resp.status_code == 201, resp.text
    return {
        "turma_id": turma_id, "disciplina_id": disciplina_id, "professor_id": professor_id,
        "alocacao_id": resp.json()["id"],
    }


async def test_criar_horario_slot_basico(client):
    """Regressão do bug de auditoria com colunas Time — antes desta
    correção, este POST 400'ava sempre com "Já existe exatamente este
    slot", mesmo sendo o primeiro slot alguma vez criado na escola."""
    escola = await criar_escola_e_gestor(client, "horarios-basico")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "dia_semana": 1,
        "hora_inicio": "08:00:00", "hora_fim": "09:00:00", "sala": "Sala 3"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/horarios/turmas/{ctx['turma_id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    grade = resp.json()
    assert len(grade) == 1
    assert grade[0]["dia_semana"] == 1
    assert grade[0]["sala"] == "Sala 3"
    assert grade[0]["hora_inicio"] == "08:00:00"


async def test_criar_horario_hora_fim_antes_de_inicio_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "horarios-intervalo-invalido")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "dia_semana": 1,
        "hora_inicio": "09:00:00", "hora_fim": "08:00:00"
    })
    assert resp.status_code == 422, resp.text


async def test_horario_bloqueia_sobreposicao_da_mesma_turma(client):
    """RN01: a mesma turma não pode ter duas aulas (mesmo de
    disciplinas diferentes) que se cruzem no mesmo dia."""
    escola = await criar_escola_e_gestor(client, "horarios-rn01-turma")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, date.today().year)
    disciplina_a_id = await _criar_disciplina(client, headers, "Matemática")
    disciplina_b_id = await _criar_disciplina(client, headers, "Português")
    professor_a_id, _ = await _criar_professor_com_token(client, headers, f"Prof. A {sufixo_unico()}")
    professor_b_id, _ = await _criar_professor_com_token(client, headers, f"Prof. B {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_a_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_id, "disciplina_id": disciplina_a_id})
    alocacao_a_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/professores/{professor_b_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_id, "disciplina_id": disciplina_b_id})
    alocacao_b_id = resp.json()["id"]

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_a_id, "dia_semana": 2, "hora_inicio": "08:00:00", "hora_fim": "09:00:00"
    })
    assert resp.status_code == 201, resp.text

    # Mesma turma, mesmo dia, intervalo sobreposto — disciplina/professor diferentes, mas é a mesma turma.
    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_b_id, "dia_semana": 2, "hora_inicio": "08:30:00", "hora_fim": "09:30:00"
    })
    assert resp.status_code == 400, resp.text
    assert "turma já tem" in resp.json()["detail"]


async def test_horario_bloqueia_sobreposicao_do_mesmo_professor(client):
    """RN02: o mesmo professor não pode lecionar em duas turmas
    diferentes ao mesmo tempo."""
    escola = await criar_escola_e_gestor(client, "horarios-rn02-professor")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    turma_a_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    turma_b_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Duplo {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_a_id, "disciplina_id": disciplina_id})
    alocacao_a_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/professores/{professor_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_b_id, "disciplina_id": disciplina_id})
    alocacao_b_id = resp.json()["id"]

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_a_id, "dia_semana": 3, "hora_inicio": "10:00:00", "hora_fim": "11:00:00"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_b_id, "dia_semana": 3, "hora_inicio": "10:30:00", "hora_fim": "11:30:00"
    })
    assert resp.status_code == 400, resp.text
    assert "professor já tem" in resp.json()["detail"]


async def test_horario_bloqueia_sobreposicao_da_mesma_sala(client):
    """RN03: duas turmas diferentes não podem ter aula à mesma hora na
    mesma sala física — só se ambos os slots tiverem sala preenchida."""
    escola = await criar_escola_e_gestor(client, "horarios-rn03-sala")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    turma_a_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    turma_b_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_a_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Sala A {sufixo_unico()}")
    professor_b_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Sala B {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_a_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_a_id, "disciplina_id": disciplina_id})
    alocacao_a_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/professores/{professor_b_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_b_id, "disciplina_id": disciplina_id})
    alocacao_b_id = resp.json()["id"]

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_a_id, "dia_semana": 4, "hora_inicio": "14:00:00", "hora_fim": "15:00:00", "sala": "Lab 1"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_b_id, "dia_semana": 4, "hora_inicio": "14:30:00", "hora_fim": "15:30:00", "sala": "lab 1"
    })
    assert resp.status_code == 400, resp.text
    assert "sala" in resp.json()["detail"].lower()


async def test_horario_sem_sala_nunca_gera_conflito_de_sala(client):
    """Duas turmas diferentes, mesma hora, ambas SEM sala definida —
    não deve disparar RN03 (aulas online/por definir)."""
    escola = await criar_escola_e_gestor(client, "horarios-sem-sala")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    turma_a_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    turma_b_id = await _preparar_turma_com_vaga(client, headers, ano_letivo)
    disciplina_id = await _criar_disciplina(client, headers)
    professor_a_id, _ = await _criar_professor_com_token(client, headers, f"Prof. X {sufixo_unico()}")
    professor_b_id, _ = await _criar_professor_com_token(client, headers, f"Prof. Y {sufixo_unico()}")

    resp = await client.post(f"/api/v1/professores/{professor_a_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_a_id, "disciplina_id": disciplina_id})
    alocacao_a_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/professores/{professor_b_id}/alocacoes", headers=headers,
                              json={"turma_id": turma_b_id, "disciplina_id": disciplina_id})
    alocacao_b_id = resp.json()["id"]

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_a_id, "dia_semana": 5, "hora_inicio": "08:00:00", "hora_fim": "09:00:00"
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": alocacao_b_id, "dia_semana": 5, "hora_inicio": "08:00:00", "hora_fim": "09:00:00"
    })
    assert resp.status_code == 201, resp.text


async def test_horario_atualizar_e_remover(client):
    escola = await criar_escola_e_gestor(client, "horarios-crud")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)

    resp = await client.post("/api/v1/horarios", headers=headers, json={
        "alocacao_id": ctx["alocacao_id"], "dia_semana": 1, "hora_inicio": "08:00:00", "hora_fim": "09:00:00"
    })
    horario_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/horarios/{horario_id}", headers=headers, json={"sala": "Sala 7"})
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/horarios/turmas/{ctx['turma_id']}", headers=headers)
    assert resp.json()[0]["sala"] == "Sala 7"

    resp = await client.delete(f"/api/v1/horarios/{horario_id}", headers=headers)
    assert resp.status_code in (200, 204), resp.text

    resp = await client.get(f"/api/v1/horarios/turmas/{ctx['turma_id']}", headers=headers)
    assert resp.json() == []


async def test_horario_professor_nao_pode_gerir_so_ler(client):
    """_PODE_GERIR (criar/editar/apagar) é GESTOR/SECRETARIA; consulta
    da própria grade fica aberta a qualquer funcionário staff."""
    escola = await criar_escola_e_gestor(client, "horarios-rbac-professor")
    headers = auth_headers(escola["token"])
    ctx = await _preparar_alocacao(client, headers, date.today().year)
    _, token_outro_professor = await _criar_professor_com_token(client, headers, f"Prof. Leitor {sufixo_unico()}")
    headers_professor = auth_headers(token_outro_professor)

    resp = await client.post("/api/v1/horarios", headers=headers_professor, json={
        "alocacao_id": ctx["alocacao_id"], "dia_semana": 1, "hora_inicio": "08:00:00", "hora_fim": "09:00:00"
    })
    assert resp.status_code == 403, resp.text

    resp = await client.get(f"/api/v1/horarios/turmas/{ctx['turma_id']}", headers=headers_professor)
    assert resp.status_code == 200, resp.text


async def test_horario_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "horarios-iso-a")
    escola_b = await criar_escola_e_gestor(client, "horarios-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    ctx = await _preparar_alocacao(client, headers_a, date.today().year)

    resp = await client.post("/api/v1/horarios", headers=headers_b, json={
        "alocacao_id": ctx["alocacao_id"], "dia_semana": 1, "hora_inicio": "08:00:00", "hora_fim": "09:00:00"
    })
    assert resp.status_code == 404, resp.text
