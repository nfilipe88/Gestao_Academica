"""Perfil SUPORTE — equipa da plataforma que ajuda as escolas: tickets,
consulta das escolas (só leitura), desbloquear pessoas (2FA, IPs) e
eventos de segurança. Nada mais: não suspende escolas, não mexe em
planos/faturação/permissões/nomes nem cria contas, e não vê dados
académicos de nenhuma escola."""
import re
from datetime import date

from app.core import fila_notificacoes
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_auth_rbac import _rotas_admin
from tests.test_dois_fatores import _ativar, _capturar_emails, _login
from tests.test_planos_por_aluno_modulo import _criar_super_admin
from tests.test_recibo_pagamento import _preparar_contrato_com_2_parcelas

# O que o Suporte pode fazer em /admin — tudo o resto tem de dar 403.
_ROTAS_DO_SUPORTE = {
    ("GET", "/api/v1/admin/tenants"),
    ("GET", "/api/v1/admin/tenants/{tenant_id}/usuarios"),
    ("POST", "/api/v1/admin/tenants/{tenant_id}/usuarios/{usuario_id}/dois-fatores/desativar"),
    ("GET", "/api/v1/admin/tickets"),
    ("GET", "/api/v1/admin/tickets/{ticket_id}"),
    ("POST", "/api/v1/admin/tickets/{ticket_id}/mensagens"),
    ("PATCH", "/api/v1/admin/tickets/{ticket_id}/estado"),
    ("GET", "/api/v1/admin/seguranca/eventos"),
    ("GET", "/api/v1/admin/seguranca/bloqueios"),
    ("DELETE", "/api/v1/admin/seguranca/bloqueios/{ip}"),
}


async def _criar_suporte(client, headers_sa) -> dict:
    email = f"suporte.{sufixo_unico()}@teste.pt"
    resp = await client.post("/api/v1/admin/equipa", headers=headers_sa, json={
        "nome_completo": "Ana Suporte", "email": email, "palavra_passe": "SuporteTeste123!",
    })
    assert resp.status_code == 201, resp.text
    login = await client.post("/api/v1/auth/login", data={"username": email, "password": "SuporteTeste123!"})
    assert login.status_code == 200, login.text
    return {"id": resp.json()["id"], "email": email, "token": login.json()["access_token"]}


async def test_super_admin_cria_e_lista_a_equipa(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    suporte = await _criar_suporte(client, headers_sa)

    equipa = (await client.get("/api/v1/admin/equipa", headers=headers_sa)).json()
    membro = next(m for m in equipa if m["id"] == suporte["id"])
    assert membro["perfil_acesso"] == "SUPORTE" and membro["ativo"] is True

    # Palavra-passe fraca e e-mail repetido recusados.
    resp = await client.post("/api/v1/admin/equipa", headers=headers_sa, json={
        "nome_completo": "Fraca", "email": f"x.{sufixo_unico()}@teste.pt", "palavra_passe": "curta",
    })
    assert resp.status_code == 422
    resp = await client.post("/api/v1/admin/equipa", headers=headers_sa, json={
        "nome_completo": "Repetido", "email": suporte["email"], "palavra_passe": "SuporteTeste123!",
    })
    assert resp.status_code == 400


async def test_suporte_so_entra_nas_rotas_de_apoio(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    headers = auth_headers((await _criar_suporte(client, headers_sa))["token"])

    escola = await criar_escola_e_gestor(client, "suporte-rotas")
    for caminho in ("/api/v1/admin/tenants", f"/api/v1/admin/tenants/{escola['tenant_id']}/usuarios",
                    "/api/v1/admin/tickets", "/api/v1/admin/seguranca/eventos", "/api/v1/admin/seguranca/bloqueios"):
        resp = await client.get(caminho, headers=headers)
        assert resp.status_code == 200, (caminho, resp.text)

    # Todas as outras rotas de /admin (incluindo as que vierem a existir) — 403.
    fake_id = "00000000-0000-0000-0000-000000000000"
    falhas = []
    for metodo, caminho in _rotas_admin():
        if (metodo, caminho) in _ROTAS_DO_SUPORTE:
            continue
        resp = await client.request(metodo, re.sub(r"\{[^}]+\}", fake_id, caminho), headers=headers, json={})
        if resp.status_code != 403:
            falhas.append((metodo, caminho, resp.status_code))
    assert not falhas, f"rotas de /admin acessíveis ao Suporte: {falhas}"


async def test_suporte_nao_ve_dados_das_escolas_nem_mexe_em_permissoes(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    headers = auth_headers((await _criar_suporte(client, headers_sa))["token"])
    for metodo, caminho in (("GET", "/api/v1/alunos"), ("GET", "/api/v1/usuarios"),
                            ("PUT", "/api/v1/permissoes/perfis/GESTOR")):
        resp = await client.request(metodo, caminho, headers=headers, json={"nome": "Chefe"})
        assert resp.status_code == 403, (caminho, resp.status_code)

    # Uma fatura real de uma escola: esta rota aceita qualquer sessão (as famílias
    # também a usam), mas o Suporte pertence ao tenant da plataforma e o RLS esconde-lhe
    # os dados de qualquer escola — nunca a vê.
    escola = await criar_escola_e_gestor(client, "suporte-fatura")
    faturas = await _preparar_contrato_com_2_parcelas(client, auth_headers(escola["token"]), date.today().year)
    fatura_id = faturas[0]["id"]
    assert (await client.get(f"/api/v1/financeiro/faturas/{fatura_id}", headers=auth_headers(escola["token"]))).status_code == 200
    assert (await client.get(f"/api/v1/financeiro/faturas/{fatura_id}", headers=headers)).status_code == 404


async def test_suporte_desbloqueia_quem_perdeu_o_email(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "suporte-2fa")
    await _ativar(client, escola, enviados)
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    suporte = await _criar_suporte(client, headers_sa)

    resp = await client.post(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/usuarios/{escola['usuario_id']}/dois-fatores/desativar",
        headers=auth_headers(suporte["token"]),
    )
    assert resp.status_code == 200, resp.text
    resp = await _login(client, escola)
    assert "access_token" in resp.json()


async def test_suspender_suporte_corta_o_acesso_e_nunca_um_super_admin(client):
    sa = await _criar_super_admin(client)
    headers_sa = auth_headers(sa["access_token"])
    suporte = await _criar_suporte(client, headers_sa)

    resp = await client.patch(f"/api/v1/admin/equipa/{suporte['id']}/ativo", headers=headers_sa, json={"ativo": False})
    assert resp.status_code == 200 and resp.json()["ativo"] is False
    assert (await client.get("/api/v1/admin/tickets", headers=auth_headers(suporte["token"]))).status_code == 401
    login = await client.post("/api/v1/auth/login", data={"username": suporte["email"], "password": "SuporteTeste123!"})
    assert login.status_code == 403

    resp = await client.patch(f"/api/v1/admin/equipa/{sa['utilizador']['id']}/ativo", headers=headers_sa, json={"ativo": False})
    assert resp.status_code == 400


async def test_alertas_de_seguranca_graves_chegam_ao_suporte(client, monkeypatch):
    enviados: list[dict] = []

    async def _agendar(_f, **kwargs):
        enviados.append(kwargs)

    monkeypatch.setattr(fila_notificacoes, "agendar_email", _agendar)
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    suporte = await _criar_suporte(client, headers_sa)
    await client.get("/api/v1/alunos", params={"q": "../../etc/passwd"})
    assert any(e["destinatario"] == suporte["email"] for e in enviados)
