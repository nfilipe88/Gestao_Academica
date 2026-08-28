"""
Fase 5 (segurança de sessão): access token curto + refresh token com
rotação, revogação real (logout, suspensão de utilizador) e política
de força da palavra-passe.

Corre sem REDIS_URL configurada (fallback em memória do processo, ver
app/core/revogacao.py) — como os testes correm todos no mesmo processo
Python, a revogação em memória funciona corretamente aqui, o mesmo
comportamento que um ambiente com uma única instância do back-end teria.
"""
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def test_login_devolve_access_e_refresh_token(client):
    escola = await criar_escola_e_gestor(client, "tokens")
    resp = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["access_token"]
    assert corpo["refresh_token"]
    assert corpo["access_token"] != corpo["refresh_token"]


async def test_refresh_token_gera_novo_access_token(client):
    escola = await criar_escola_e_gestor(client, "refresh-ok")
    login = (await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})).json()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200
    novo = resp.json()
    assert novo["access_token"] and novo["access_token"] != login["access_token"]
    assert novo["refresh_token"] and novo["refresh_token"] != login["refresh_token"]

    # O novo access token funciona normalmente.
    resp = await client.get("/api/v1/configuracoes", headers=auth_headers(novo["access_token"]))
    assert resp.status_code == 200


async def test_refresh_token_e_de_uso_unico_reusar_falha(client):
    """Rotação: cada refresh token só pode ser trocado uma vez. Voltar a
    usar o mesmo depois de já ter sido trocado é tratado como possível
    roubo — é recusado."""
    escola = await criar_escola_e_gestor(client, "refresh-reuso")
    login = (await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})).json()

    primeira = await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert primeira.status_code == 200

    segunda = await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert segunda.status_code == 401


async def test_refresh_token_invalido_e_recusado(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "isto-nao-existe"})
    assert resp.status_code == 401


async def test_logout_revoga_o_access_token_imediatamente(client):
    """Antes da Fase 5, "Sair do Sistema" só apagava o token no browser —
    o token continuava válido no back-end até expirar sozinho. Agora um
    pedido com o MESMO token, depois do logout, tem de ser recusado."""
    escola = await criar_escola_e_gestor(client, "logout")
    login = (await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})).json()
    headers = auth_headers(login["access_token"])

    # Antes do logout, o token funciona normalmente.
    resp = await client.get("/api/v1/configuracoes", headers=headers)
    assert resp.status_code == 200

    resp = await client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200

    # Depois do logout, o MESMO access token deixa de funcionar — mesmo
    # sem ter expirado (a assinatura/exp continuam válidos).
    resp = await client.get("/api/v1/configuracoes", headers=headers)
    assert resp.status_code == 401

    # O refresh token também foi revogado.
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 401


async def test_suspender_utilizador_revoga_a_sessao_ja_aberta(client):
    """Centro da Fase 5: suspender uma conta tinha, antes, efeito só em
    LOGINS novos — uma sessão já aberta continuava a funcionar até o
    token expirar sozinho (documentado como limitação aceite em
    app/database/models.py::Usuario.ativo). Agora tem de parar
    imediatamente."""
    gestor = await criar_escola_e_gestor(client, "suspende")
    headers_gestor = auth_headers(gestor["token"])

    suf = sufixo_unico()
    email_secretaria = f"secretaria.suspende.{suf}@teste.pt"
    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers_gestor, json={
        "nome_completo": "Secretaria de Teste", "email": email_secretaria, "palavra_passe": "SenhaTeste123!"
    })
    assert resp.status_code == 201, resp.text
    secretaria_id = resp.json()["id"]

    login_secretaria = (await client.post(
        "/api/v1/auth/login", data={"username": email_secretaria, "password": "SenhaTeste123!"}
    )).json()
    headers_secretaria = auth_headers(login_secretaria["access_token"])

    # A sessão da secretaria funciona normalmente antes da suspensão.
    resp = await client.get("/api/v1/configuracoes", headers=headers_secretaria)
    assert resp.status_code == 200

    resp = await client.patch(f"/api/v1/usuarios/{secretaria_id}/ativo", headers=headers_gestor, json={"ativo": False})
    assert resp.status_code == 200

    # O MESMO token, já emitido antes da suspensão, deixa de funcionar de imediato.
    resp = await client.get("/api/v1/configuracoes", headers=headers_secretaria)
    assert resp.status_code == 401


async def test_registo_com_palavra_passe_fraca_e_recusado(client):
    suf = sufixo_unico()
    resp = await client.post("/api/v1/auth/registo", json={
        "nome_fantasia": f"Escola Senha Fraca {suf}", "nif": suf,
        "nome_gestor": "Gestor Teste", "email_gestor": f"gestor.senhafraca.{suf}@teste.pt",
        "palavra_passe": "tudominusculo1",  # sem maiúscula
    })
    assert resp.status_code == 422
