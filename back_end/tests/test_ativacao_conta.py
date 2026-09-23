"""Ativação de conta por e-mail (registo self-service de uma escola
nova) — sem isto, o registo criava logo uma conta com login imediato;
passa a exigir clicar num link enviado por e-mail primeiro (ver
cruds/auth.py::registar_escola/ativar_conta/autenticar). Sem SMTP real
neste ambiente de testes, o "clique no link" é simulado chamando
crud_auth.registar_escola diretamente para obter o token em texto
limpo (só assim — a API HTTP real esconde-o dentro do e-mail, nunca o
devolve na resposta, por desenho); os testes que só precisam de
confirmar o BLOQUEIO usam a API real (POST /auth/registo) sem precisar
do token nenhum.

Note: tests/conftest.py::criar_escola_e_gestor já ativa a conta
diretamente na BD para todos os OUTROS ~68 ficheiros de teste que só
querem uma escola pronta a usar — não repetido aqui.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.cruds import auth as crud_auth
from app.database.models_usuarios import ContaAtivacaoToken
from app.database.session import AsyncSessionLocalSistema
from app.schemas.auth import RegistoInicial
from tests.conftest import sufixo_unico


async def _registar_via_crud(prefixo: str) -> dict:
    """Mesmo caminho de tests/conftest.py::criar_escola_e_gestor, só
    que chamando o crud diretamente (não a API HTTP) para obter o
    token de ativação em texto limpo."""
    suf = sufixo_unico()
    email = f"gestor.{prefixo}.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    dados = RegistoInicial(
        nome_fantasia=f"Escola {prefixo} {suf}", nif=suf,
        nome_gestor=f"Gestor {prefixo}", email_gestor=email, palavra_passe=senha,
    )
    tenant, usuario, token = await crud_auth.registar_escola(dados)
    return {"tenant_id": str(tenant.id), "usuario_id": str(usuario.id), "email": email, "senha": senha, "token": token}


async def test_registo_bloqueia_login_antes_de_ativar(client):
    suf = sufixo_unico()
    email = f"gestor.bloqueio.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    resp = await client.post("/api/v1/auth/registo", json={
        "nome_fantasia": f"Escola Bloqueio {suf}", "nif": suf,
        "nome_gestor": "Gestor Bloqueio", "aceitou_termos": True, "email_gestor": email, "palavra_passe": senha,
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 403, resp.text
    assert "ativa" in resp.json()["detail"].lower()


async def test_ativar_conta_com_token_valido_permite_login(client):
    escola = await _registar_via_crud("ativacao-ok")

    # Login recusado ANTES de ativar — confirma que _registar_via_crud
    # produz o mesmo estado pré-ativação do fluxo HTTP real.
    resp = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    assert resp.status_code == 403, resp.text

    resp = await client.post("/api/v1/auth/ativar-conta", json={"token": escola["token"]})
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": escola["senha"]})
    assert resp.status_code == 200, resp.text


async def test_ativar_conta_token_invalido_e_recusado(client):
    resp = await client.post("/api/v1/auth/ativar-conta", json={"token": "token-que-nao-existe"})
    assert resp.status_code == 400, resp.text


async def test_ativar_conta_token_ja_usado_e_recusado(client):
    escola = await _registar_via_crud("ativacao-reuso")
    resp = await client.post("/api/v1/auth/ativar-conta", json={"token": escola["token"]})
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/auth/ativar-conta", json={"token": escola["token"]})
    assert resp.status_code == 400, resp.text


async def test_ativar_conta_token_expirado_e_recusado(client):
    escola = await _registar_via_crud("ativacao-expirado")
    async with AsyncSessionLocalSistema() as db:
        await db.execute(
            update(ContaAtivacaoToken)
            .where(ContaAtivacaoToken.usuario_id == escola["usuario_id"])
            .values(expira_em=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await db.commit()

    resp = await client.post("/api/v1/auth/ativar-conta", json={"token": escola["token"]})
    assert resp.status_code == 400, resp.text
