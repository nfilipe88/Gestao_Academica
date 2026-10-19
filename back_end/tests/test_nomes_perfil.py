"""Nomes dos perfis editáveis pelo Super Admin (ex.: GESTOR → "Diretor
Geral") — o código e as permissões ficam iguais, só muda o que se lê.

ATENÇÃO: perfil_nome é uma tabela GLOBAL e a BD de testes não é limpa
entre execuções — todo o teste que muda um nome repõe-no num finally.
"""
from sqlalchemy import update

from app.core import nomes_perfil
from app.database.models_permissoes import PerfilNome
from app.database.session import AsyncSessionLocalSistema
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_auth_rbac import _criar_secretaria_com_token
from tests.test_planos_por_aluno_modulo import _criar_super_admin


async def _repor(codigo: str, nome: str) -> None:
    async with AsyncSessionLocalSistema() as db:
        await db.execute(update(PerfilNome).where(PerfilNome.codigo == codigo).values(nome=nome))
        await db.commit()
    nomes_perfil.invalidar()


async def _nome_atual(client, headers, codigo: str) -> str:
    perfis = (await client.get("/api/v1/permissoes/perfis", headers=headers)).json()
    return next(p["nome"] for p in perfis if p["codigo"] == codigo)


async def test_qualquer_pessoa_com_sessao_le_os_nomes(client):
    escola = await criar_escola_e_gestor(client, "nomes-ler")
    token_secretaria = await _criar_secretaria_com_token(client, auth_headers(escola["token"]), escola["nif"])
    resp = await client.get("/api/v1/permissoes/perfis", headers=auth_headers(token_secretaria))
    assert resp.status_code == 200
    assert [p["codigo"] for p in resp.json()] == ["SUPER_ADMIN", "GESTOR", "SECRETARIA", "PROFESSOR", "ALUNO", "RESPONSAVEL", "SUPORTE"]
    assert (await client.get("/api/v1/permissoes/perfis")).status_code == 401


async def test_super_admin_renomeia_e_o_nome_aparece_nas_mensagens(client):
    escola = await criar_escola_e_gestor(client, "nomes-renomear")
    headers_gestor = auth_headers(escola["token"])
    token_secretaria = await _criar_secretaria_com_token(client, headers_gestor, escola["nif"])
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    original = await _nome_atual(client, headers_sa, "GESTOR")
    try:
        resp = await client.put("/api/v1/permissoes/perfis/GESTOR", headers=headers_sa, json={"nome": "  Diretor   Geral "})
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"codigo": "GESTOR", "nome": "Diretor Geral"}

        # O nome novo chega a toda a gente…
        assert await _nome_atual(client, headers_gestor, "GESTOR") == "Diretor Geral"
        # …e às mensagens de acesso negado.
        resp = await client.get("/api/v1/usuarios", headers=auth_headers(token_secretaria))
        assert resp.status_code == 403 and "Diretor Geral" in resp.json()["detail"]
        # As permissões continuam as mesmas: o Gestor continua a entrar.
        assert (await client.get("/api/v1/usuarios", headers=headers_gestor)).status_code == 200
    finally:
        await _repor("GESTOR", original)


async def test_so_o_super_admin_renomeia(client):
    escola = await criar_escola_e_gestor(client, "nomes-rbac")
    resp = await client.put("/api/v1/permissoes/perfis/GESTOR", headers=auth_headers(escola["token"]), json={"nome": "Chefe"})
    assert resp.status_code == 403
    assert await _nome_atual(client, auth_headers(escola["token"]), "GESTOR") != "Chefe"


async def test_nome_repetido_ou_invalido_e_recusado(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    nome_gestor = await _nome_atual(client, headers_sa, "GESTOR")
    original_secretaria = await _nome_atual(client, headers_sa, "SECRETARIA")
    try:
        resp = await client.put("/api/v1/permissoes/perfis/SECRETARIA", headers=headers_sa, json={"nome": nome_gestor.upper()})
        assert resp.status_code == 400
        assert (await client.put("/api/v1/permissoes/perfis/SECRETARIA", headers=headers_sa, json={"nome": "X"})).status_code == 422
        assert (await client.put("/api/v1/permissoes/perfis/INEXISTENTE", headers=headers_sa, json={"nome": "Novo"})).status_code == 404
        assert await _nome_atual(client, headers_sa, "SECRETARIA") == original_secretaria
    finally:
        await _repor("SECRETARIA", original_secretaria)
