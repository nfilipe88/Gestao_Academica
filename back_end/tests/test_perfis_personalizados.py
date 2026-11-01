"""Perfis da escola (bloco D2): o Gestor cria perfis a partir da Secretaria
ou do Professor, com menos permissões — terceira camada do Mapa de
Permissões (app/core/mapa_permissoes.py). Cada teste usa escolas novas
(tudo é por tenant; nada toca no mapa base global)."""
import uuid

from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_auth_rbac import _criar_secretaria_com_token
from tests.test_comportamento import _criar_professor_com_token
from tests.test_planos_por_aluno_modulo import _criar_super_admin

_OPS = ("pode_criar", "pode_ler", "pode_atualizar", "pode_apagar")
_HORARIOS = f"/api/v1/horarios/turmas/{uuid.uuid4()}"
_DESPESAS = "/api/v1/financeiro/despesas"


async def _escola_com_secretaria(client, prefixo: str) -> tuple[dict, dict, str, dict]:
    escola = await criar_escola_e_gestor(client, prefixo)
    headers = auth_headers(escola["token"])
    token_sec = await _criar_secretaria_com_token(client, headers, escola["nif"])
    usuarios = (await client.get("/api/v1/usuarios", headers=headers)).json()["items"]
    sec_id = next(u["id"] for u in usuarios if u["perfil_acesso"] == "SECRETARIA")
    return escola, headers, sec_id, auth_headers(token_sec)


async def _criar_perfil(client, headers, nome: str, base: str = "SECRETARIA") -> dict:
    resp = await client.post("/api/v1/perfis-personalizados", headers=headers, json={"nome": nome, "perfil_base": base})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _celula(perfil: dict, modulo: str) -> dict:
    return next(p for p in perfil["permissoes"] if p["modulo"] == modulo)


async def _definir(client, headers, perfil_id, modulo: str, **ops):
    atual = {op: False for op in _OPS}
    atual.update(ops)
    return await client.put(f"/api/v1/perfis-personalizados/{perfil_id}/permissoes", headers=headers,
                            json={"modulo": modulo, **atual})


async def test_perfil_da_escola_restringe_quem_o_tem(client):
    escola, headers, sec_id, headers_sec = await _escola_com_secretaria(client, "perfil-escola-tesouraria")

    # Começa igual à Secretaria na escola.
    perfil = await _criar_perfil(client, headers, "Tesouraria")
    assert perfil["perfil_base"] == "SECRETARIA" and perfil["n_utilizadores"] == 0
    horarios = _celula(perfil, "Horários")
    assert all(horarios[op] == horarios[f"limite_{op}"] for op in _OPS)
    visao = _celula(perfil, "Visão Geral")
    # Linha só informativa: não decide nada, mostra o do perfil base.
    assert visao["informativo"] is True
    assert all(visao[op] == visao[f"limite_{op}"] for op in _OPS)

    # Tesouraria: sem Horários.
    resp = await _definir(client, headers, perfil["id"], "Horários")
    assert resp.status_code == 200, resp.text
    assert not any(_celula(resp.json(), "Horários")[op] for op in _OPS)

    # Antes de o ter, a Secretaria vê os horários.
    assert (await client.get(_HORARIOS, headers=headers_sec)).status_code == 200

    resp = await client.put(f"/api/v1/usuarios/{sec_id}/perfil-personalizado", headers=headers,
                            json={"perfil_personalizado_id": perfil["id"]})
    assert resp.status_code == 200, resp.text

    # Efeito imediato, sem novo login; a mensagem usa o nome do perfil da escola.
    resp = await client.get(_HORARIOS, headers=headers_sec)
    assert resp.status_code == 403
    assert "Tesouraria" in resp.json()["detail"]
    # O resto continua igual à Secretaria.
    assert (await client.get(_DESPESAS, headers=headers_sec)).status_code == 200

    # O menu sabe o que esconder.
    minhas = (await client.get("/api/v1/permissoes/minhas", headers=headers_sec)).json()
    assert minhas["perfil_personalizado"] == "Tesouraria"
    assert minhas["modulos"]["Horários"]["pode_ler"] is False
    assert minhas["modulos"]["Financeiro"]["pode_ler"] is True

    # Gestão de Acessos mostra o perfil da escola.
    usuarios = (await client.get("/api/v1/usuarios", headers=headers)).json()["items"]
    linha = next(u for u in usuarios if u["id"] == sec_id)
    assert linha["perfil_personalizado_nome"] == "Tesouraria"
    auditoria = (await client.get("/api/v1/usuarios/auditoria", headers=headers)).json()["items"]
    assert any(r["acao"] == "PERFIL_ESCOLA" and "Tesouraria" in (r["detalhe"] or "") for r in auditoria)

    # Tirar o perfil devolve o acesso.
    resp = await client.put(f"/api/v1/usuarios/{sec_id}/perfil-personalizado", headers=headers,
                            json={"perfil_personalizado_id": None})
    assert resp.status_code == 200, resp.text
    assert (await client.get(_HORARIOS, headers=headers_sec)).status_code == 200


async def test_perfil_da_escola_nunca_tem_mais_que_o_base(client):
    escola, headers, _, _ = await _escola_com_secretaria(client, "perfil-escola-teto")

    # O Professor não tem Financeiro no mapa base — um perfil a partir dele também não.
    perfil_prof = await _criar_perfil(client, headers, "Coordenação", base="PROFESSOR")
    assert not any(_celula(perfil_prof, "Financeiro")[f"limite_{op}"] for op in _OPS)
    resp = await _definir(client, headers, perfil_prof["id"], "Financeiro", pode_ler=True)
    assert resp.status_code == 400
    assert "menos" in resp.json()["detail"]

    # A escola tira à Secretaria apagar no Financeiro: o perfil da escola fica com esse teto.
    linhas = (await client.get("/api/v1/permissoes", headers=headers)).json()
    fin_sec = next(l for l in linhas if l["modulo"] == "Financeiro" and l["perfil"] == "secretaria")
    resp = await client.put(f"/api/v1/permissoes/{fin_sec['id']}/escola", headers=headers,
                            json={**{op: fin_sec[op] for op in _OPS}, "pode_apagar": False})
    assert resp.status_code == 200, resp.text
    perfil_sec = await _criar_perfil(client, headers, "Tesouraria")
    assert _celula(perfil_sec, "Financeiro")["limite_pode_apagar"] is False
    resp = await _definir(client, headers, perfil_sec["id"], "Financeiro", pode_ler=True, pode_apagar=True)
    assert resp.status_code == 400

    # Linha só informativa e módulo inexistente.
    assert (await _definir(client, headers, perfil_sec["id"], "Visão Geral", pode_ler=True)).status_code == 400
    assert (await _definir(client, headers, perfil_sec["id"], "Não Existe")).status_code == 404

    # Só Secretaria ou Professor como base.
    resp = await client.post("/api/v1/perfis-personalizados", headers=headers, json={"nome": "Vice", "perfil_base": "GESTOR"})
    assert resp.status_code == 400


async def test_atribuicao_so_a_quem_tem_o_perfil_base(client):
    escola, headers, sec_id, _ = await _escola_com_secretaria(client, "perfil-escola-atribuicao")
    await _criar_professor_com_token(client, headers, "Prof Perfil Escola")
    usuarios = (await client.get("/api/v1/usuarios", headers=headers)).json()["items"]
    prof_id = next(u["id"] for u in usuarios if u["perfil_acesso"] == "PROFESSOR")
    gestor_id = next(u["id"] for u in usuarios if u["perfil_acesso"] == "GESTOR")

    perfil_sec = await _criar_perfil(client, headers, "Tesouraria")
    for alvo in (prof_id, gestor_id):
        resp = await client.put(f"/api/v1/usuarios/{alvo}/perfil-personalizado", headers=headers,
                                json={"perfil_personalizado_id": perfil_sec["id"]})
        assert resp.status_code == 400, resp.text

    # Perfil de outra escola: não existe para esta.
    outra = await criar_escola_e_gestor(client, "perfil-escola-outra")
    perfil_outra = await _criar_perfil(client, auth_headers(outra["token"]), "Tesouraria")
    resp = await client.put(f"/api/v1/usuarios/{sec_id}/perfil-personalizado", headers=headers,
                            json={"perfil_personalizado_id": perfil_outra["id"]})
    assert resp.status_code == 404


async def test_mudar_o_perfil_base_ou_apagar_o_perfil_volta_ao_base(client):
    escola, headers, sec_id, headers_sec = await _escola_com_secretaria(client, "perfil-escola-apagar")
    perfil = await _criar_perfil(client, headers, "Tesouraria")
    await _definir(client, headers, perfil["id"], "Horários")
    await client.put(f"/api/v1/usuarios/{sec_id}/perfil-personalizado", headers=headers,
                     json={"perfil_personalizado_id": perfil["id"]})
    assert (await client.get(_HORARIOS, headers=headers_sec)).status_code == 403
    assert (await client.get("/api/v1/perfis-personalizados", headers=headers)).json()[0]["n_utilizadores"] == 1

    resp = await client.delete(f"/api/v1/perfis-personalizados/{perfil['id']}", headers=headers)
    assert resp.status_code == 204
    assert (await client.get(_HORARIOS, headers=headers_sec)).status_code == 200
    usuarios = (await client.get("/api/v1/usuarios", headers=headers)).json()["items"]
    assert next(u for u in usuarios if u["id"] == sec_id)["perfil_personalizado_id"] is None

    # Mudar de Secretaria para Gestor tira o perfil da escola (partia da Secretaria).
    perfil = await _criar_perfil(client, headers, "Tesouraria")
    await client.put(f"/api/v1/usuarios/{sec_id}/perfil-personalizado", headers=headers,
                     json={"perfil_personalizado_id": perfil["id"]})
    resp = await client.patch(f"/api/v1/usuarios/{sec_id}/perfil", headers=headers, json={"perfil_acesso": "GESTOR"})
    assert resp.status_code == 200, resp.text
    usuarios = (await client.get("/api/v1/usuarios", headers=headers)).json()["items"]
    assert next(u for u in usuarios if u["id"] == sec_id)["perfil_personalizado_id"] is None


async def test_nomes_e_isolamento_entre_escolas(client):
    escola, headers, _, headers_sec = await _escola_com_secretaria(client, "perfil-escola-nomes")
    perfil = await _criar_perfil(client, headers, "Tesouraria")

    # Repetido (sem distinguir maiúsculas) e igual a um perfil da plataforma.
    for nome in ("  tesouraria ", "Secretaria"):
        resp = await client.post("/api/v1/perfis-personalizados", headers=headers, json={"nome": nome, "perfil_base": "SECRETARIA"})
        assert resp.status_code == 400, resp.text
    resp = await client.patch(f"/api/v1/perfis-personalizados/{perfil['id']}", headers=headers, json={"nome": "Tesouraria Central"})
    assert resp.status_code == 200 and resp.json()["nome"] == "Tesouraria Central"

    # Outra escola: pode usar o mesmo nome, não vê nem mexe nos desta.
    outra = await criar_escola_e_gestor(client, "perfil-escola-nomes-outra")
    headers_outra = auth_headers(outra["token"])
    await _criar_perfil(client, headers_outra, "Tesouraria Central")
    lista_outra = (await client.get("/api/v1/perfis-personalizados", headers=headers_outra)).json()
    assert [p["id"] for p in lista_outra] != [perfil["id"]] and len(lista_outra) == 1
    assert (await client.patch(f"/api/v1/perfis-personalizados/{perfil['id']}", headers=headers_outra, json={"nome": "X Y"})).status_code == 404
    assert (await _definir(client, headers_outra, perfil["id"], "Horários")).status_code == 404
    assert (await client.delete(f"/api/v1/perfis-personalizados/{perfil['id']}", headers=headers_outra)).status_code == 404

    # Só o Gestor gere perfis da escola.
    assert (await client.get("/api/v1/perfis-personalizados", headers=headers_sec)).status_code == 403
    assert (await client.post("/api/v1/perfis-personalizados", headers=headers_sec,
                              json={"nome": "Eu Mesma", "perfil_base": "SECRETARIA"})).status_code == 403


async def test_minhas_permissoes_da_equipa_da_plataforma(client):
    headers_sa = auth_headers((await _criar_super_admin(client))["access_token"])
    resp = await client.get("/api/v1/permissoes/minhas", headers=headers_sa)
    assert resp.status_code == 200
    assert resp.json() == {"modulos": None, "perfil_personalizado": None}
