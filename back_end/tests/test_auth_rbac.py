"""Autenticação e controlo de acesso por perfil (RBAC)."""
import re

from main import app
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


def _rotas_admin() -> list[tuple[str, str]]:
    """Descobre, diretamente na app FastAPI, TODAS as rotas registadas
    sob /api/v1/admin — em vez de uma lista hardcoded que ficaria
    desatualizada a cada rota nova (ex.: as de Estatísticas/Despesas
    cross-tenant acrescentadas depois deste teste já existir), isto
    continua a cobrir 100% das rotas de admin.py para sempre, incluindo
    as que ainda não foram escritas."""
    rotas = []
    for rota in app.routes:
        caminho = getattr(rota, "path", "")
        if not caminho.startswith("/api/v1/admin"):
            continue
        for metodo in sorted(getattr(rota, "methods", set()) - {"HEAD", "OPTIONS"}):
            rotas.append((metodo, caminho))
    return rotas


async def test_rbac_bloqueia_gestor_de_todas_as_rotas_admin(client):
    """Nenhuma rota de /admin pode ser acedida por um Gestor — cobre TODAS
    as rotas registadas (descobertas via introspeção da app, não uma
    lista escrita à mão), incluindo as de Estatísticas/Despesas
    cross-tenant acrescentadas para o Super Admin. Confirmado à parte
    que o RBAC (Depends(exigir_perfil(...))) é resolvido antes da
    validação do corpo/query — um corpo vazio ou UUID inventado no path
    nunca mascara o 403 com um 422, por isso um único pedido por rota
    (sem montar dados válidos para cada schema) já prova o bloqueio."""
    escola = await criar_escola_e_gestor(client, "rbac-todas-admin")
    headers = auth_headers(escola["token"])
    fake_id = "00000000-0000-0000-0000-000000000000"

    rotas = _rotas_admin()
    assert len(rotas) >= 25, "menos rotas de /admin do que o esperado — a introspeção pode estar a falhar"

    falhas = []
    for metodo, caminho in rotas:
        caminho_resolvido = re.sub(r"\{[^}]+\}", fake_id, caminho)
        resp = await client.request(metodo, caminho_resolvido, headers=headers, json={})
        if resp.status_code != 403:
            falhas.append((metodo, caminho_resolvido, resp.status_code))

    assert not falhas, f"rotas de /admin acessíveis a um Gestor (esperado 403 em todas): {falhas}"


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
