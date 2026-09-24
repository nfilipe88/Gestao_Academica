"""Refresh token em cookie HttpOnly (JavaScript nunca o lê) e cabeçalhos de
segurança da API — ver app/api/v1/auth.py e main.py."""
from tests.conftest import auth_headers, criar_escola_e_gestor

COOKIE = "saas_refresh"


async def _login(client, escola):
    resp = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    assert resp.status_code == 200, resp.text
    return resp


def _atributos(resp) -> str:
    return next(v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie" and v.startswith(COOKIE + "=")).lower()


async def test_login_define_cookie_httponly_samesite_strict_no_caminho_da_auth(client):
    escola = await criar_escola_e_gestor(client, "cookie-login")
    resp = await _login(client, escola)
    cookie = _atributos(resp)
    assert resp.json()["refresh_token"].lower() in cookie
    assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie and "path=/api/v1/auth" in cookie and "max-age=" in cookie


async def test_refresh_so_com_cookie_roda_o_token_e_o_reuso_falha(client):
    escola = await criar_escola_e_gestor(client, "cookie-refresh")
    login = (await _login(client, escola)).json()

    resp = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE}={login['refresh_token']}"})
    assert resp.status_code == 200, resp.text
    novo = resp.json()
    assert novo["access_token"] and novo["refresh_token"] != login["refresh_token"]
    assert novo["refresh_token"].lower() in _atributos(resp), "o cookie é renovado a cada rotação"

    reuso = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE}={login['refresh_token']}"})
    assert reuso.status_code == 401
    assert "max-age=0" in _atributos(reuso), "um refresh recusado limpa o cookie"


async def test_refresh_sem_cookie_nem_corpo_e_recusado(client):
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_logout_so_com_cookie_revoga_o_refresh_e_limpa_o_cookie(client):
    escola = await criar_escola_e_gestor(client, "cookie-logout")
    login = (await _login(client, escola)).json()
    headers = {**auth_headers(login["access_token"]), "Cookie": f"{COOKIE}={login['refresh_token']}"}

    resp = await client.post("/api/v1/auth/logout", headers=headers, json={})
    assert resp.status_code == 200, resp.text
    assert "max-age=0" in _atributos(resp)

    depois = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"{COOKIE}={login['refresh_token']}"})
    assert depois.status_code == 401


async def test_refresh_pelo_corpo_continua_a_funcionar_para_clientes_de_api(client):
    escola = await criar_escola_e_gestor(client, "cookie-corpo")
    login = (await _login(client, escola)).json()
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200, resp.text


async def test_respostas_da_api_levam_cabecalhos_de_seguranca(client):
    resp = await client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"]
    login = await client.post("/api/v1/auth/login", data={"username": "nao@existe.pt", "password": "x"})
    assert login.headers["cache-control"] == "no-store"
