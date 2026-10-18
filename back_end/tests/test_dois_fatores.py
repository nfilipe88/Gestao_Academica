"""Verificação em dois passos por e-mail (auditoria de segurança, bloco 5)
— opcional, ligada pelo próprio no Perfil. Ver cruds/dois_fatores.py."""
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.core import fila_notificacoes
from app.database.models import Usuario
from app.database.models_usuarios import DesafioDoisFatores
from app.database.session import AsyncSessionLocalSistema
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_planos_por_aluno_modulo import _criar_super_admin


def _capturar_emails(monkeypatch) -> list[dict]:
    enviados: list[dict] = []

    async def _agendar_falso(_funcao_envio, **kwargs):
        enviados.append(kwargs)

    monkeypatch.setattr(fila_notificacoes, "agendar_email", _agendar_falso)
    return enviados


def _ultimo_codigo(enviados: list[dict]) -> str:
    corpo = next(e["corpo_html"] for e in reversed(enviados) if "Código" in e["assunto"])
    return re.search(r"letter-spacing:6px;\">(\d{6})<", corpo).group(1)


def _codigo_errado(certo: str) -> str:
    return f"{(int(certo) + 1) % 10**6:06d}"


async def _login(client, escola):
    return await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})


async def _ativar(client, escola, enviados) -> None:
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/perfil/dois-fatores/ativar", headers=headers, json={"senha_atual": escola["senha"]})
    assert resp.status_code == 200, resp.text
    resp = await client.post("/api/v1/perfil/dois-fatores/confirmar", headers=headers, json={
        "desafio": resp.json()["desafio"], "codigo": _ultimo_codigo(enviados),
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["dois_fatores_ativo"] is True


# ==========================================
# Ligar e desligar no Perfil
# ==========================================
async def test_ativar_exige_palavra_passe_e_o_codigo_do_email(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-ativar")
    headers = auth_headers(escola["token"])
    assert (await client.get("/api/v1/perfil", headers=headers)).json()["dois_fatores_ativo"] is False

    resp = await client.post("/api/v1/perfil/dois-fatores/ativar", headers=headers, json={"senha_atual": "Errada12345!"})
    assert resp.status_code == 400

    resp = await client.post("/api/v1/perfil/dois-fatores/ativar", headers=headers, json={"senha_atual": escola["senha"]})
    assert resp.status_code == 200, resp.text
    desafio = resp.json()["desafio"]
    assert "*" in resp.json()["email_mascarado"] and resp.json()["email_mascarado"] != escola["email"]
    codigo = _ultimo_codigo(enviados)

    resp = await client.post("/api/v1/perfil/dois-fatores/confirmar", headers=headers, json={
        "desafio": desafio, "codigo": _codigo_errado(codigo),
    })
    assert resp.status_code == 400
    assert (await client.get("/api/v1/perfil", headers=headers)).json()["dois_fatores_ativo"] is False

    resp = await client.post("/api/v1/perfil/dois-fatores/confirmar", headers=headers, json={"desafio": desafio, "codigo": codigo})
    assert resp.status_code == 200, resp.text
    assert resp.json()["dois_fatores_ativo"] is True
    assert any("ativada" in e["assunto"] for e in enviados)


async def test_desativar_exige_palavra_passe_e_volta_ao_login_simples(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-desativar")
    await _ativar(client, escola, enviados)
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/perfil/dois-fatores/desativar", headers=headers, json={"senha_atual": "Errada12345!"})
    assert resp.status_code == 400
    resp = await client.post("/api/v1/perfil/dois-fatores/desativar", headers=headers, json={"senha_atual": escola["senha"]})
    assert resp.status_code == 200 and resp.json()["dois_fatores_ativo"] is False
    assert any("desativada" in e["assunto"] for e in enviados)

    resp = await _login(client, escola)
    assert resp.status_code == 200 and "access_token" in resp.json()


# ==========================================
# Login com a verificação ligada
# ==========================================
async def test_login_so_emite_sessao_depois_do_codigo(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-login")
    await _ativar(client, escola, enviados)

    resp = await _login(client, escola)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    # Só a palavra-passe certa não chega: nenhum token, nenhum cookie de sessão.
    assert corpo["requer_dois_fatores"] is True and "access_token" not in corpo
    assert "saas_refresh" not in resp.headers.get("set-cookie", "")
    codigo = _ultimo_codigo(enviados)

    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": corpo["desafio"], "codigo": _codigo_errado(codigo)})
    assert resp.status_code == 400 and "Restam 4" in resp.json()["detail"]

    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": corpo["desafio"], "codigo": codigo})
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("set-cookie", "").startswith("saas_refresh=")
    token = resp.json()["access_token"]
    assert (await client.get("/api/v1/perfil", headers=auth_headers(token))).status_code == 200

    # O mesmo código não serve duas vezes.
    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": corpo["desafio"], "codigo": codigo})
    assert resp.status_code == 400


async def test_cinco_erros_matam_o_codigo(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-tentativas")
    await _ativar(client, escola, enviados)

    desafio = (await _login(client, escola)).json()["desafio"]
    codigo = _ultimo_codigo(enviados)
    for _ in range(5):
        resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": desafio, "codigo": _codigo_errado(codigo)})
        assert resp.status_code == 400
    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": desafio, "codigo": codigo})
    assert resp.status_code == 400


async def test_reenviar_troca_o_codigo_e_tem_limite(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-reenviar")
    await _ativar(client, escola, enviados)

    desafio = (await _login(client, escola)).json()["desafio"]
    codigo_antigo = _ultimo_codigo(enviados)
    for _ in range(3):
        resp = await client.post("/api/v1/auth/login/dois-fatores/reenviar", json={"desafio": desafio})
        assert resp.status_code == 200, resp.text
    resp = await client.post("/api/v1/auth/login/dois-fatores/reenviar", json={"desafio": desafio})
    assert resp.status_code == 429

    codigo_novo = _ultimo_codigo(enviados)
    if codigo_novo != codigo_antigo:
        resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": desafio, "codigo": codigo_antigo})
        assert resp.status_code == 400
    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": desafio, "codigo": codigo_novo})
    assert resp.status_code == 200, resp.text


async def test_codigo_expirado_e_recusado(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-expirado")
    await _ativar(client, escola, enviados)

    desafio = (await _login(client, escola)).json()["desafio"]
    async with AsyncSessionLocalSistema() as db:
        await db.execute(
            update(DesafioDoisFatores)
            .where(DesafioDoisFatores.usuario_id == escola["usuario_id"], DesafioDoisFatores.usado.is_(False))
            .values(expira_em=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await db.commit()
    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": desafio, "codigo": _ultimo_codigo(enviados)})
    assert resp.status_code == 400


async def test_conta_suspensa_entre_os_dois_passos_nao_entra(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-suspensa")
    await _ativar(client, escola, enviados)

    desafio = (await _login(client, escola)).json()["desafio"]
    async with AsyncSessionLocalSistema() as db:
        await db.execute(update(Usuario).where(Usuario.id == escola["usuario_id"]).values(ativo=False))
        await db.commit()
    resp = await client.post("/api/v1/auth/login/dois-fatores", json={"desafio": desafio, "codigo": _ultimo_codigo(enviados)})
    assert resp.status_code == 403


async def test_codigo_de_ativacao_nao_serve_para_entrar(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-finalidade")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/perfil/dois-fatores/ativar", headers=headers, json={"senha_atual": escola["senha"]})
    desafio_ativacao = resp.json()["desafio"]

    resp = await client.post("/api/v1/auth/login/dois-fatores", json={
        "desafio": desafio_ativacao, "codigo": _ultimo_codigo(enviados),
    })
    assert resp.status_code == 400


# ==========================================
# Quem gere os acessos desliga a de outra pessoa (perdeu o e-mail)
# ==========================================
async def _secretaria_com_dois_fatores(client, escola, enviados) -> dict:
    headers_gestor = auth_headers(escola["token"])
    email = f"sec.2fa.{escola['nif']}@teste.pt"
    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers_gestor, json={
        "nome_completo": "Secretaria 2FA", "email": email, "palavra_passe": "SenhaTeste123!",
    })
    assert resp.status_code == 201, resp.text
    secretaria = {"id": resp.json()["id"], "email": email, "senha": "SenhaTeste123!"}
    secretaria["token"] = (await _login(client, secretaria)).json()["access_token"]
    await _ativar(client, secretaria, enviados)
    return secretaria


async def test_gestor_desativa_a_verificacao_de_outra_pessoa(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-gestor-reset")
    headers_gestor = auth_headers(escola["token"])
    secretaria = await _secretaria_com_dois_fatores(client, escola, enviados)

    lista = (await client.get("/api/v1/usuarios", headers=headers_gestor)).json()["items"]
    assert next(u for u in lista if u["id"] == secretaria["id"])["dois_fatores_ativo"] is True

    resp = await client.post(f"/api/v1/usuarios/{secretaria['id']}/dois-fatores/desativar", headers=headers_gestor)
    assert resp.status_code == 200, resp.text
    assert resp.json()["dois_fatores_ativo"] is False

    # Volta a entrar só com a palavra-passe, foi avisada, e fica na auditoria.
    resp = await _login(client, secretaria)
    assert resp.status_code == 200 and "access_token" in resp.json()
    assert any(e["destinatario"] == secretaria["email"] and "pela direção" in e["assunto"] for e in enviados)
    auditoria = (await client.get("/api/v1/usuarios/auditoria", headers=headers_gestor)).json()["items"]
    assert any(r["acao"] == "DESATIVACAO_2FA" and r["usuario_alvo_id"] == secretaria["id"] for r in auditoria)


async def test_gestor_nao_desativa_a_propria_por_aqui(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-gestor-proprio")
    await _ativar(client, escola, enviados)
    resp = await client.post(
        f"/api/v1/usuarios/{escola['usuario_id']}/dois-fatores/desativar", headers=auth_headers(escola["token"])
    )
    assert resp.status_code == 400
    assert (await client.get("/api/v1/perfil", headers=auth_headers(escola["token"]))).json()["dois_fatores_ativo"] is True


async def test_so_o_gestor_da_propria_escola_pode_desativar(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-reset-rbac")
    secretaria = await _secretaria_com_dois_fatores(client, escola, enviados)
    url = f"/api/v1/usuarios/{escola['usuario_id']}/dois-fatores/desativar"

    # A Secretaria não gere acessos.
    assert (await client.post(url, headers=auth_headers(secretaria["token"]))).status_code == 403
    # O Gestor de outra escola não encontra ninguém desta.
    outra = await criar_escola_e_gestor(client, "2fa-reset-outra")
    resp = await client.post(f"/api/v1/usuarios/{secretaria['id']}/dois-fatores/desativar", headers=auth_headers(outra["token"]))
    assert resp.status_code == 404


async def test_super_admin_desativa_a_de_um_gestor_de_qualquer_escola(client, monkeypatch):
    """Escola com um único Gestor que perdeu o e-mail: só o Super Admin o desbloqueia."""
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "2fa-superadmin")
    await _ativar(client, escola, enviados)
    super_admin = await _criar_super_admin(client)

    resp = await client.post(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/usuarios/{escola['usuario_id']}/dois-fatores/desativar",
        headers=auth_headers(super_admin["access_token"]),
    )
    assert resp.status_code == 200, resp.text
    resp = await _login(client, escola)
    assert resp.status_code == 200 and "access_token" in resp.json()
