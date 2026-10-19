"""Mapa de Permissões a decidir o acesso (app/core/mapa_permissoes.py).

ATENÇÃO: permissao_modulo é uma tabela GLOBAL e a BD de testes não é
limpa entre execuções — todo o teste que mexe no mapa base repõe-no num
finally. As restrições por escola (permissao_modulo_escola) são por
tenant, cada teste usa escolas novas.
"""
import uuid

from sqlalchemy import select

from app.core import mapa_permissoes
from app.database.models_usuarios import EventoSeguranca
from app.database.session import AsyncSessionLocalSistema
from main import app
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_auth_rbac import _criar_secretaria_com_token
from tests.test_comportamento import _criar_professor_com_token
from tests.test_planos_por_aluno_modulo import _criar_super_admin

_OPS = mapa_permissoes.OPERACOES


async def _linha(client, headers, modulo: str, perfil: str) -> dict:
    resp = await client.get("/api/v1/permissoes", headers=headers)
    assert resp.status_code == 200, resp.text
    return next(l for l in resp.json() if l["modulo"] == modulo and l["perfil"] == perfil)


def _corpo(linha: dict, **mudancas) -> dict:
    corpo = {op: linha[op] for op in _OPS}
    corpo.update(mudancas)
    return corpo


# ==========================================
# Alinhamento: no primeiro dia ninguém ganhou nem perdeu acesso
# ==========================================
async def test_mapa_base_esta_alinhado_com_o_codigo(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    teto = mapa_permissoes.teto_do_codigo(app)
    linhas = (await client.get("/api/v1/permissoes", headers=headers_sa)).json()
    diferencas = [
        (l["modulo"], l["perfil"], op) for l in linhas if (l["modulo"], l["perfil"]) in teto
        for op in _OPS if l[op] != teto[(l["modulo"], l["perfil"])][op]
    ]
    # A única diferença é a decidida: o Professor fora do Financeiro.
    assert sorted(diferencas) == sorted(
        [("Financeiro", "professor", op) for op in ("pode_criar", "pode_ler", "pode_atualizar")]
    )


async def test_professor_ja_nao_entra_no_financeiro(client):
    escola = await criar_escola_e_gestor(client, "mapa-prof-financeiro")
    _, token_professor = await _criar_professor_com_token(client, auth_headers(escola["token"]), "Prof Mapa")
    resp = await client.get(f"/api/v1/financeiro/faturas/{uuid.uuid4()}", headers=auth_headers(token_professor))
    assert resp.status_code == 403
    assert "Financeiro" in resp.json()["detail"]

    # A recusa fica registada com a pessoa identificada (não conta para bloquear o IP da escola).
    async with AsyncSessionLocalSistema() as db:
        evento = (await db.execute(
            select(EventoSeguranca).where(
                EventoSeguranca.tenant_id == uuid.UUID(escola["tenant_id"]), EventoSeguranca.tipo == "ACESSO_NEGADO"
            )
        )).scalars().first()
    assert evento is not None and evento.usuario_id is not None and "Mapa de Permissões" in evento.detalhe


# ==========================================
# Mapa da escola: o Gestor restringe só a própria escola
# ==========================================
async def test_gestor_restringe_a_propria_escola_e_nao_as_outras(client):
    escola = await criar_escola_e_gestor(client, "mapa-escola-a")
    headers_gestor = auth_headers(escola["token"])
    token_sec = await _criar_secretaria_com_token(client, headers_gestor, escola["nif"])
    outra = await criar_escola_e_gestor(client, "mapa-escola-b")
    token_sec_outra = await _criar_secretaria_com_token(client, auth_headers(outra["token"]), outra["nif"])

    linha = await _linha(client, headers_gestor, "Financeiro", "secretaria")
    assert linha["pode_criar"] and linha["escola_pode_criar"]
    resp = await client.put(f"/api/v1/permissoes/{linha['id']}/escola", headers=headers_gestor,
                            json=_corpo(linha, pode_criar=False))
    assert resp.status_code == 200, resp.text
    assert resp.json()["escola_pode_criar"] is False and resp.json()["pode_criar"] is True  # o base não mudou

    # A Secretaria desta escola já não cria no Financeiro (o mapa decide antes do corpo do pedido)…
    assert (await client.post("/api/v1/financeiro/despesas", headers=auth_headers(token_sec), json={})).status_code == 403
    # …mas continua a ver.
    assert (await client.get("/api/v1/financeiro/despesas", headers=auth_headers(token_sec))).status_code == 200
    # A da outra escola não é afetada (passa o mapa; falha só a validação do corpo vazio).
    assert (await client.post("/api/v1/financeiro/despesas", headers=auth_headers(token_sec_outra), json={})).status_code == 422

    # Repor igual ao base apaga a restrição.
    resp = await client.put(f"/api/v1/permissoes/{linha['id']}/escola", headers=headers_gestor, json=_corpo(linha))
    assert resp.status_code == 200 and resp.json()["escola_pode_criar"] is True
    assert (await client.post("/api/v1/financeiro/despesas", headers=auth_headers(token_sec), json={})).status_code == 422


async def test_gestor_nao_da_mais_do_que_o_base_nem_se_tranca_fora(client):
    escola = await criar_escola_e_gestor(client, "mapa-limites-gestor")
    headers = auth_headers(escola["token"])

    # Acima do mapa base (Professor no Financeiro): recusado.
    linha = await _linha(client, headers, "Financeiro", "professor")
    resp = await client.put(f"/api/v1/permissoes/{linha['id']}/escola", headers=headers, json=_corpo(linha, pode_ler=True))
    assert resp.status_code == 400

    # O Gestor nunca perde o acesso às Configurações.
    linha = await _linha(client, headers, "Configurações", "gestor")
    resp = await client.put(f"/api/v1/permissoes/{linha['id']}/escola", headers=headers, json=_corpo(linha, pode_atualizar=False))
    assert resp.status_code == 400

    # E não mexe no mapa base (que é de todas as escolas).
    linha = await _linha(client, headers, "Cursos", "secretaria")
    resp = await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers, json=_corpo(linha, pode_apagar=False))
    assert resp.status_code == 403


# ==========================================
# Mapa base: o Super Admin, para todas as escolas, nunca acima do código
# ==========================================
async def test_super_admin_restringe_o_base_para_todas_as_escolas(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    escola = await criar_escola_e_gestor(client, "mapa-base")
    token_sec = await _criar_secretaria_com_token(client, auth_headers(escola["token"]), escola["nif"])
    linha = await _linha(client, headers_sa, "Financeiro", "secretaria")
    try:
        resp = await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers_sa, json=_corpo(linha, pode_apagar=False))
        assert resp.status_code == 200, resp.text
        resp = await client.delete(f"/api/v1/financeiro/despesas/{uuid.uuid4()}", headers=auth_headers(token_sec))
        assert resp.status_code == 403
    finally:
        await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers_sa, json=_corpo(linha))
        mapa_permissoes.invalidar_cache()


async def test_super_admin_nao_da_acima_do_codigo_nem_mexe_na_propria_coluna(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    linha = await _linha(client, headers_sa, "Cursos", "professor")
    assert linha["codigo_pode_apagar"] is False
    resp = await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers_sa, json=_corpo(linha, pode_apagar=True))
    assert resp.status_code == 400

    linha = await _linha(client, headers_sa, "Cursos", "super_admin")
    resp = await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers_sa, json=_corpo(linha))
    assert resp.status_code == 400


async def test_linhas_sem_rotas_sao_so_informativas(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    linha = await _linha(client, headers_sa, "Visão Geral", "gestor")
    assert linha["informativo"] is True
