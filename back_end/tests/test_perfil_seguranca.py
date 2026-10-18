"""Auditoria de segurança (bloco 2): tomada de conta pela Área de Perfil.

Quem tivesse só uma sessão aberta (computador partilhado, token roubado)
conseguia mudar o email da conta sem saber a palavra-passe — e com isso
desviar a recuperação de palavra-passe para si. E mudar a palavra-passe
não terminava as outras sessões, por isso quem já a sabia continuava
com acesso."""
from app.core import fila_notificacoes
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


def _capturar_emails(monkeypatch) -> list[dict]:
    enviados: list[dict] = []

    async def _agendar_falso(_funcao_envio, **kwargs):
        enviados.append(kwargs)

    monkeypatch.setattr(fila_notificacoes, "agendar_email", _agendar_falso)
    return enviados


async def test_mudar_email_exige_palavra_passe_atual(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "perfil-email")
    headers = auth_headers(escola["token"])
    novo_email = f"outro.{sufixo_unico()}@teste.pt"

    resp = await client.put("/api/v1/perfil", headers=headers, json={"nome_completo": "Gestor", "email": novo_email})
    assert resp.status_code == 400

    resp = await client.put("/api/v1/perfil", headers=headers, json={
        "nome_completo": "Gestor", "email": novo_email, "senha_atual": "PalavraErrada123!"
    })
    assert resp.status_code == 400
    assert (await client.get("/api/v1/perfil", headers=headers)).json()["email"] == escola["email"]

    resp = await client.put("/api/v1/perfil", headers=headers, json={
        "nome_completo": "Gestor", "email": novo_email, "senha_atual": escola["senha"]
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == novo_email

    # O aviso vai para o endereço ANTIGO — o único que o dono legítimo ainda controla.
    avisos = [e for e in enviados if e["destinatario"] == escola["email"] and "alterado" in e["assunto"]]
    assert len(avisos) == 1 and novo_email in avisos[0]["corpo_html"]


async def test_mudar_so_o_nome_nao_exige_palavra_passe(client):
    escola = await criar_escola_e_gestor(client, "perfil-nome")
    headers = auth_headers(escola["token"])
    resp = await client.put("/api/v1/perfil", headers=headers, json={"nome_completo": "Nome Novo", "email": escola["email"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["nome_completo"] == "Nome Novo"


async def test_mudar_palavra_passe_termina_as_outras_sessoes(client, monkeypatch):
    _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "perfil-senha")

    # Uma segunda sessão (outro dispositivo) da mesma pessoa.
    login = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    assert login.status_code == 200
    outra_sessao = login.json()

    resp = await client.post("/api/v1/perfil/alterar-senha", headers=auth_headers(escola["token"]), json={
        "senha_atual": escola["senha"], "nova_senha": "NovaSenha456!"
    })
    assert resp.status_code == 200, resp.text
    novo_token = resp.json()["access_token"]

    # A outra sessão morre de imediato, tal como o token antigo de quem
    # fez o pedido — este continua só com o token novo.
    assert (await client.get("/api/v1/perfil", headers=auth_headers(outra_sessao["access_token"]))).status_code == 401
    assert (await client.get("/api/v1/perfil", headers=auth_headers(escola["token"]))).status_code == 401
    assert (await client.get("/api/v1/perfil", headers=auth_headers(novo_token))).status_code == 200

    # O refresh token novo (no cookie, como no browser) continua a renovar a sessão.
    cookie = next(v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie" and v.startswith("saas_refresh="))
    refresh_novo = cookie.split(";", 1)[0].split("=", 1)[1]
    resp = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"saas_refresh={refresh_novo}"})
    assert resp.status_code == 200, resp.text
    assert (await client.get("/api/v1/perfil", headers=auth_headers(resp.json()["access_token"]))).status_code == 200

    # O refresh token da outra sessão já não serve (e, como qualquer token
    # revogado reapresentado, é tratado como roubo — ver
    # cruds/auth.py::renovar_access_token).
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": outra_sessao["refresh_token"]})
    assert resp.status_code == 401

    login_antigo = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    assert login_antigo.status_code == 401


async def test_mudar_palavra_passe_com_a_atual_errada_nao_termina_sessoes(client):
    escola = await criar_escola_e_gestor(client, "perfil-senha-errada")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/perfil/alterar-senha", headers=headers, json={
        "senha_atual": "PalavraErrada123!", "nova_senha": "NovaSenha456!"
    })
    assert resp.status_code == 400
    assert (await client.get("/api/v1/perfil", headers=headers)).status_code == 200
