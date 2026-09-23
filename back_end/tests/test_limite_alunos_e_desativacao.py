"""Limite de alunos do plano SaaS (com isenção do Super Admin) e
desativação/reativação de alunos pelo Gestor — nada é eliminado (retenção
legal de 15 anos), só desativado; ver app/core/limites_plano.py."""
import asyncio
from datetime import date, timedelta

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_planos_por_aluno_modulo import _criar_super_admin
from tests.test_matricula_financeiro import _preparar_turma_com_vaga


async def _escola_com_limite(client, limite: int, prefixo: str):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    escola = await criar_escola_e_gestor(client, prefixo)
    resp = await client.post("/api/v1/admin/planos", headers=headers_admin, json={
        "nome": f"Plano Limitado {sufixo_unico()}", "preco_por_aluno": "100.00", "limite_alunos": limite, "modulos": [],
    })
    assert resp.status_code == 201, resp.text
    resp = await client.put(f"/api/v1/admin/tenants/{escola['tenant_id']}/assinatura", headers=headers_admin, json={
        "plano_id": resp.json()["id"], "proxima_cobranca": (date.today() + timedelta(days=30)).isoformat(),
    })
    assert resp.status_code == 200, resp.text
    return headers_admin, escola, auth_headers(escola["token"])


async def _criar_aluno(client, headers, nome="Aluno"):
    return await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2015-01-01",
    })


async def test_plano_com_limite_recusa_alunos_a_mais(client):
    _, _, headers = await _escola_com_limite(client, 2, "limite-recusa")
    assert (await _criar_aluno(client, headers)).status_code == 201
    assert (await _criar_aluno(client, headers)).status_code == 201
    resp = await _criar_aluno(client, headers)
    assert resp.status_code == 403
    assert "Limite de 2" in resp.json()["detail"]


async def test_isencao_do_super_admin_ignora_o_limite(client):
    headers_admin, escola, headers = await _escola_com_limite(client, 1, "limite-isencao")
    assert (await _criar_aluno(client, headers)).status_code == 201
    assert (await _criar_aluno(client, headers)).status_code == 403

    resp = await client.patch(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/isencao-limite-alunos", headers=headers_admin, json={"isento": True}
    )
    assert resp.status_code == 200, resp.text
    assert (await _criar_aluno(client, headers)).status_code == 201

    await client.patch(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/isencao-limite-alunos", headers=headers_admin, json={"isento": False}
    )
    assert (await _criar_aluno(client, headers)).status_code == 403


async def test_so_super_admin_concede_isencao(client):
    escola = await criar_escola_e_gestor(client, "isencao-403")
    resp = await client.patch(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/isencao-limite-alunos",
        headers=auth_headers(escola["token"]), json={"isento": True},
    )
    assert resp.status_code == 403


async def test_desativar_aluno_liberta_vaga_e_reativar_volta_a_validar_limite(client):
    _, _, headers = await _escola_com_limite(client, 1, "limite-desativar")
    aluno_id = (await _criar_aluno(client, headers, "Aluno A")).json()["id"]
    assert (await _criar_aluno(client, headers)).status_code == 403

    resp = await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", headers=headers, json={"ativo": False})
    assert resp.status_code == 200, resp.text
    assert resp.json()["ativo"] is False

    outro = await _criar_aluno(client, headers, "Aluno B")
    assert outro.status_code == 201

    # A vaga já foi ocupada por B — reativar A ultrapassaria o limite.
    resp = await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", headers=headers, json={"ativo": True})
    assert resp.status_code == 403


async def test_aluno_desativado_continua_listado_com_historico_e_filtra_por_ativo(client):
    escola = await criar_escola_e_gestor(client, "desativar-lista")
    headers = auth_headers(escola["token"])
    aluno_id = (await _criar_aluno(client, headers, "Aluno Histórico")).json()["id"]
    await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", headers=headers, json={"ativo": False})

    todos = (await client.get("/api/v1/alunos", headers=headers)).json()["items"]
    assert any(a["id"] == aluno_id and a["ativo"] is False for a in todos)
    inativos = (await client.get("/api/v1/alunos?ativo=false", headers=headers)).json()["items"]
    assert [a["id"] for a in inativos] == [aluno_id]
    ativos = (await client.get("/api/v1/alunos?ativo=true", headers=headers)).json()["items"]
    assert ativos == []


async def test_desativar_aluno_bloqueia_o_login_dele_e_reativar_restaura(client):
    escola = await criar_escola_e_gestor(client, "desativar-login")
    headers = auth_headers(escola["token"])
    aluno_id = (await _criar_aluno(client, headers, "Aluno Com Acesso")).json()["id"]
    email = f"aluno.desativar.{sufixo_unico()}@teste.pt"
    resp = await client.post(f"/api/v1/alunos/{aluno_id}/criar-acesso", headers=headers,
                             json={"email": email, "palavra_passe": "SenhaTeste123!"})
    assert resp.status_code == 201, resp.text
    login = {"username": email, "password": "SenhaTeste123!"}
    assert (await client.post("/api/v1/auth/login", data=login)).status_code == 200

    await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", headers=headers, json={"ativo": False})
    assert (await client.post("/api/v1/auth/login", data=login)).status_code in (401, 403)

    await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", headers=headers, json={"ativo": True})
    assert (await client.post("/api/v1/auth/login", data=login)).status_code == 200


async def test_aluno_desativado_nao_pode_ser_matriculado(client):
    escola = await criar_escola_e_gestor(client, "desativar-matricula")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, date.today().year)
    aluno_id = (await _criar_aluno(client, headers)).json()["id"]
    await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", headers=headers, json={"ativo": False})
    resp = await client.post("/api/v1/matriculas", headers=headers, json={
        "aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": date.today().year,
    })
    assert resp.status_code == 400
    assert "desativado" in resp.json()["detail"]


async def test_pedido_anonimo_nao_desativa_alunos(client):
    escola = await criar_escola_e_gestor(client, "desativar-rbac")
    aluno_id = (await _criar_aluno(client, auth_headers(escola["token"]))).json()["id"]
    resp = await client.patch(f"/api/v1/alunos/{aluno_id}/ativo", json={"ativo": False})
    assert resp.status_code == 401


async def test_desativar_e_reativar_escola_nunca_apaga_nada(client):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    escola = await criar_escola_e_gestor(client, "escola-desativar")
    headers = auth_headers(escola["token"])
    aluno_id = (await _criar_aluno(client, headers, "Aluno Da Escola")).json()["id"]

    resp = await client.patch(f"/api/v1/admin/tenants/{escola['tenant_id']}/status", headers=headers_admin, json={"status": "SUSPENSO"})
    assert resp.status_code == 200 and "desativada" in resp.json()["mensagem"]
    login = {"username": escola["email"], "password": escola["senha"]}
    assert (await client.post("/api/v1/auth/login", data=login)).status_code in (401, 403)

    # A claim "iat" do JWT tem resolução de 1 segundo, a revogação guarda o instante exato: sem esta
    # pausa, um token emitido logo a seguir, no mesmo segundo da suspensão, seria dado como revogado.
    await asyncio.sleep(1.1)
    resp = await client.patch(f"/api/v1/admin/tenants/{escola['tenant_id']}/status", headers=headers_admin, json={"status": "ATIVO"})
    assert resp.status_code == 200 and "ativa" in resp.json()["mensagem"]
    novo_login = await client.post("/api/v1/auth/login", data=login)
    assert novo_login.status_code == 200
    resp = await client.get("/api/v1/alunos", headers=auth_headers(novo_login.json()["access_token"]))
    assert resp.status_code == 200, resp.text
    alunos = resp.json()["items"]
    assert any(a["id"] == aluno_id for a in alunos)
