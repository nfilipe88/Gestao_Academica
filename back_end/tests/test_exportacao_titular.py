"""Exportação de dados por titular (app/core/exportacao_titular.py)."""
import json

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_planos_por_aluno_modulo import _criar_super_admin


async def _aluno(client, headers, nome):
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-01-01"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_exportacao_do_aluno_traz_os_seus_dados_e_nunca_os_de_outros_nem_segredos(client):
    escola = await criar_escola_e_gestor(client, "exportar-aluno")
    headers = auth_headers(escola["token"])
    aluno = await _aluno(client, headers, "Aluno Exportado")
    irmao = await _aluno(client, headers, "Irmao Alheio")
    email = f"aluno.export.{sufixo_unico()}@teste.pt"
    assert (await client.post(f"/api/v1/alunos/{aluno}/criar-acesso", headers=headers,
                              json={"email": email, "palavra_passe": "SenhaTeste123!"})).status_code == 201
    await client.post("/api/v1/auth/login", data={"username": email, "password": "SenhaTeste123!"})

    resp_id = (await client.post("/api/v1/responsaveis", headers=headers, json={
        "nome_completo": "Mae Comum", "telefone_contato": "+244911111111"})).json()["id"]
    for a in (aluno, irmao):
        assert (await client.post(f"/api/v1/alunos/{a}/responsaveis", headers=headers, json={
            "responsavel_id": resp_id, "tipo_parentesco": "Mãe", "responsavel_financeiro": True})).status_code == 201

    resp = await client.get(f"/api/v1/privacidade/exportar/aluno/{aluno}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "attachment" in resp.headers["content-disposition"]
    corpo = resp.json()
    dados = corpo["dados"]
    texto = json.dumps(corpo)

    assert [a["nome_completo"] for a in dados["aluno"]] == ["Aluno Exportado"]
    assert dados["usuario"][0]["email"] == email
    assert len(dados["login_historico"]) >= 1, "o histórico de logins da própria pessoa faz parte dos seus dados"
    assert dados["responsavel_financeiro_legal"][0]["telefone_contato"] == "+244911111111"
    assert len(dados["aluno_responsavel"]) == 1, "só o vínculo deste aluno, não o do irmão"
    assert "Irmao Alheio" not in texto
    assert "senha_hash" not in texto and "token_hash" not in texto


async def test_exportacao_do_responsavel_e_isolada_por_escola_e_so_para_o_gestor(client):
    escola = await criar_escola_e_gestor(client, "exportar-resp")
    outra = await criar_escola_e_gestor(client, "exportar-resp-outra")
    headers = auth_headers(escola["token"])
    aluno = await _aluno(client, headers, "Filho")
    resp_id = (await client.post("/api/v1/responsaveis", headers=headers, json={
        "nome_completo": "Pai Exportado", "telefone_contato": "+244922222222"})).json()["id"]
    await client.post(f"/api/v1/alunos/{aluno}/responsaveis", headers=headers, json={
        "responsavel_id": resp_id, "tipo_parentesco": "Pai", "responsavel_financeiro": False})

    resp = await client.get(f"/api/v1/privacidade/exportar/responsavel/{resp_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    dados = resp.json()["dados"]
    assert dados["responsavel_financeiro_legal"][0]["nome_completo"] == "Pai Exportado"
    assert len(dados["aluno_responsavel"]) == 1

    # outra escola não vê titulares desta
    assert (await client.get(f"/api/v1/privacidade/exportar/responsavel/{resp_id}", headers=auth_headers(outra["token"]))).status_code == 404
    assert (await client.get(f"/api/v1/privacidade/exportar/aluno/{aluno}", headers=auth_headers(outra["token"]))).status_code == 404
    # Super Admin não é Gestor
    admin = await _criar_super_admin(client)
    assert (await client.get(f"/api/v1/privacidade/exportar/aluno/{aluno}", headers=auth_headers(admin["access_token"]))).status_code == 403


async def test_exportacao_do_utilizador_professor_inclui_a_conta_sem_hash(client):
    escola = await criar_escola_e_gestor(client, "exportar-user")
    resp = await client.get(f"/api/v1/privacidade/exportar/usuario/{escola['usuario_id']}", headers=auth_headers(escola["token"]))
    assert resp.status_code == 200, resp.text
    dados = resp.json()["dados"]
    assert dados["usuario"][0]["id"] == escola["usuario_id"]
    assert "senha_hash" not in json.dumps(dados)


async def test_exportacao_desce_ate_matriculas_notas_contratos_e_faturas_sem_apanhar_outros_alunos(client):
    from tests.test_estatisticas import _montar_cenario
    escola = await criar_escola_e_gestor(client, "exportar-profundo")
    headers = auth_headers(escola["token"])
    cenario = await _montar_cenario(client, headers)
    alunos = (await client.get("/api/v1/alunos?page=1&page_size=50", headers=headers)).json()["items"]
    dezasseis = next(a for a in alunos if a["nome_completo"] == "Aluno Dezasseis Anos")

    dados = (await client.get(f"/api/v1/privacidade/exportar/aluno/{dezasseis['id']}", headers=headers)).json()["dados"]
    assert len(dados["matricula"]) == 1
    assert len(dados["contrato_financeiro"]) == 1
    assert len(dados["fatura_mensalidade"]) == 12
    assert len(dados["registro_nota"]) == 1, sorted(dados)
    assert "Aluno Doze Anos" not in json.dumps(dados)
