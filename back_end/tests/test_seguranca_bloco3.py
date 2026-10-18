"""Auditoria de segurança (bloco 3): formulários públicos, prazo da
candidatura pública, chave dos tokens e HSTS. Os uploads estão em
test_uploads_seguranca.py."""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.core import recaptcha
from app.core.security import validar_chave_jwt
from app.database.models_crm import LeadCandidato
from app.database.session import AsyncSessionLocalSistema
from main import app
from tests.conftest import criar_escola_e_gestor
from tests.test_foto_perfil import _PNG_1X1

_TICKET = {"nome": "Visitante", "email": "visitante@teste.pt", "assunto": "Dúvida", "mensagem": "Olá"}


# ==========================================
# Formulário de Contacto público (tickets)
# ==========================================
async def test_ticket_publico_bloqueia_spam_do_mesmo_ip(client):
    respostas = [(await client.post("/api/v1/public/tickets", json=_TICKET)).status_code for _ in range(6)]
    assert respostas[:5] == [201] * 5
    assert respostas[5] == 429


async def test_ticket_publico_exige_recaptcha_valido(client, monkeypatch):
    async def _recusar(token, ip=None):
        return False

    monkeypatch.setattr(recaptcha, "token_e_valido", _recusar)
    resp = await client.post("/api/v1/public/tickets", json={**_TICKET, "recaptcha_token": "token-falso"})
    assert resp.status_code == 400


# ==========================================
# Candidatura pública: o id só serve enquanto o assistente está a ser preenchido
# ==========================================
async def test_documentos_da_candidatura_so_se_alteram_nas_primeiras_24h(client):
    escola = await criar_escola_e_gestor(client, "lead-prazo")
    tenant_id = escola["tenant_id"]
    resp = await client.post(f"/api/v1/public/{tenant_id}/leads", json={
        "nome_responsavel": "Maria Candidata", "nome_aluno_candidato": "Joãozinho",
    })
    lead_id = resp.json()["id"]
    url = f"/api/v1/public/{tenant_id}/leads/{lead_id}/documentos"

    resp = await client.post(url, params={"tipo": "FOTO"}, files={"ficheiro": ("foto.png", _PNG_1X1, "image/png")})
    assert resp.status_code == 201, resp.text
    documento_id = resp.json()["documentos"][0]["id"]

    async with AsyncSessionLocalSistema() as db:
        await db.execute(
            update(LeadCandidato).where(LeadCandidato.id == lead_id)
            .values(data_entrada=datetime.now(timezone.utc) - timedelta(hours=25))
        )
        await db.commit()

    resp = await client.post(url, params={"tipo": "FOTO"}, files={"ficheiro": ("foto.png", _PNG_1X1, "image/png")})
    assert resp.status_code == 403
    resp = await client.delete(f"{url}/{documento_id}")
    assert resp.status_code == 403


# ==========================================
# Chave de assinatura dos tokens
# ==========================================
@pytest.mark.parametrize("chave", [
    None, "", "curta-demais",
    "a" * 64,  # longa mas sem variedade
    "defina-aqui-uma-chave-secreta-longa-e-aleatoria",
    "chave-secreta-so-para-docker-compose-local-trocar-em-producao",
])
def test_chave_jwt_fraca_impede_o_arranque(chave):
    with pytest.raises(RuntimeError):
        validar_chave_jwt(chave)


def test_chave_jwt_forte_e_aceite():
    chave = "Zt3q9vXk2LmP8wRb7NcY4hJd6FsG1aQe5UoI0pTy"
    assert validar_chave_jwt(chave) == chave


# ==========================================
# HSTS
# ==========================================
async def test_hsts_so_em_pedidos_https(client):
    resp = await client.get("/api/v1/health")
    assert "strict-transport-security" not in resp.headers

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://teste.local") as cliente_https:
        resp = await cliente_https.get("/api/v1/health")
    assert resp.headers["strict-transport-security"] == "max-age=31536000"
