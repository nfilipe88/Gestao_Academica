"""Autenticação e controlo de acesso por perfil (RBAC)."""
from tests.conftest import auth_headers, criar_escola_e_gestor


async def test_login_com_credenciais_corretas_devolve_token(client):
    escola = await criar_escola_e_gestor(client, "login-ok")
    resp = await client.post(
        "/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]}
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["access_token"]
    assert corpo["utilizador"]["perfil_acesso"] == "GESTOR"


async def test_login_com_password_errada_falha(client):
    escola = await criar_escola_e_gestor(client, "login-mal")
    resp = await client.post(
        "/api/v1/auth/login", data={"username": escola["email"], "password": "password-errada-123"}
    )
    assert resp.status_code == 401


async def test_pedido_sem_token_e_recusado(client):
    resp = await client.get("/api/v1/academico/cursos")
    assert resp.status_code == 401


async def test_rbac_bloqueia_gestor_de_rota_exclusiva_super_admin(client):
    """/admin/tenants só pode ser acedida pelo Super Admin — um Gestor,
    mesmo autenticado com um token válido, tem de ser recusado."""
    escola = await criar_escola_e_gestor(client, "rbac")
    resp = await client.get("/api/v1/admin/tenants", headers=auth_headers(escola["token"]))
    assert resp.status_code == 403


async def test_limite_de_tentativas_login_bloqueia_forca_bruta(client):
    """Anti força-bruta (ver api/v1/auth.py::_verificar_limite_login) —
    depois de várias tentativas falhadas seguidas para o mesmo utilizador,
    o login tem de passar a devolver 429 em vez de continuar a tentar a
    palavra-passe indefinidamente."""
    escola = await criar_escola_e_gestor(client, "bruteforce")

    ultima_resposta = None
    for _ in range(8):
        ultima_resposta = await client.post(
            "/api/v1/auth/login", data={"username": escola["email"], "password": "errada-de-proposito"}
        )
        if ultima_resposta.status_code == 429:
            break

    assert ultima_resposta is not None and ultima_resposta.status_code == 429, (
        "o limitador de tentativas de login nunca bloqueou depois de várias falhas seguidas"
    )
