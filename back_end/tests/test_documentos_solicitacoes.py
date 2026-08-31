"""Solicitações de Documentos (pedido de emissão paga, Aluno/Responsável
-> Escola) — ver app/cruds/documentos.py. Não havia nenhum teste deste
fluxo antes desta sessão (só o de personalização de templates, em
test_documentos_templates.py).

Inclui regressão de dois bugs reais encontrados num teste exaustivo ao
vivo: (1) GET /documentos/precos (exige GESTOR) era a única rota usada
pelo Portal para preencher o <select> de "Pedir novo documento" —
sempre 403 para ALUNO/RESPONSAVEL, deixando o formulário
permanentemente sem opções; corrigido com uma rota nova,
/precos/disponiveis, aberta a ALUNO/RESPONSAVEL e já filtrada aos
tipos ativos. (2) mesmo com o <select> corrigido, o valor por omissão
do tipo escolhido no frontend estava fixo em "CERTIFICADO" — se a
escola só tivesse outro tipo ativo, o pedido falhava com "não está
disponível para pedido" sem o utilizador nunca ter tocado no campo;
corrigido no frontend (não testável aqui), mas o comportamento do
back-end que o expôs — rejeitar um tipo válido mas inativo — já fica
coberto no teste test_criar_solicitacao_tipo_inativo_e_rejeitada."""
from datetime import date

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_rematricula import _criar_aluno_matriculado_com_portal


async def _ativar_preco(client, headers, tipo: str, preco: str = "15.00") -> None:
    resp = await client.put(f"/api/v1/documentos/precos/{tipo}", headers=headers, json={"preco": preco, "ativo": True})
    assert resp.status_code == 200, resp.text


async def test_precos_disponiveis_so_lista_tipos_ativos(client):
    escola = await criar_escola_e_gestor(client, "doc-precos-disponiveis")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)
    await _ativar_preco(client, headers, "DECLARACAO")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.get("/api/v1/documentos/precos/disponiveis", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    tipos = [p["tipo_documento"] for p in resp.json()]
    assert tipos == ["DECLARACAO"], "só o tipo ativado, nunca os outros 4 (inativos por omissão)"
    assert resp.json()[0]["preco"] == 15.0


async def test_precos_disponiveis_bloqueado_para_staff(client):
    """_PODE_PEDIR é só ALUNO/RESPONSAVEL — /precos (staff) é a rota
    equivalente para GESTOR, esta rota nunca deveria ser chamada por
    perfis de funcionário."""
    escola = await criar_escola_e_gestor(client, "doc-precos-disponiveis-staff")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/documentos/precos/disponiveis", headers=headers)
    assert resp.status_code == 403, resp.text


async def test_precos_disponiveis_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "doc-precos-iso-a")
    escola_b = await criar_escola_e_gestor(client, "doc-precos-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    dados_a = await _criar_aluno_matriculado_com_portal(client, headers_a, date.today().year)
    await _ativar_preco(client, headers_b, "DECLARACAO")  # só a escola B ativa

    resp = await client.post("/api/v1/auth/login", data={"username": dados_a["email_responsavel"], "password": dados_a["senha"]})
    headers_responsavel_a = auth_headers(resp.json()["access_token"])

    resp = await client.get("/api/v1/documentos/precos/disponiveis", headers=headers_responsavel_a)
    assert resp.status_code == 200, resp.text
    assert resp.json() == [], "a escola A não ativou nada — não pode ver o preço configurado pela escola B"


async def test_criar_solicitacao_emissao_fluxo_completo(client):
    escola = await criar_escola_e_gestor(client, "doc-solicitacao-completa")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)
    await _ativar_preco(client, headers, "DECLARACAO")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.post("/api/v1/documentos/solicitacoes", headers=headers_responsavel, json={
        "tipo_documento": "DECLARACAO", "formato_entrega": "DIGITAL"
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PENDENTE_PAGAMENTO"
    solicitacao_id = resp.json()["id"]

    resp = await client.get("/api/v1/documentos/solicitacoes/minhas", headers=headers_responsavel)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1

    # A Secretaria vê o mesmo pedido do lado de gestão.
    resp = await client.get("/api/v1/documentos/solicitacoes", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1

    resp = await client.patch(f"/api/v1/documentos/solicitacoes/{solicitacao_id}/cancelar", headers=headers)
    assert resp.status_code == 200, resp.text


async def test_criar_solicitacao_tipo_inativo_e_rejeitada(client):
    """Regressão direta do bug: pedir um tipo válido (existe em
    TIPOS_DOCUMENTO) mas que a escola nunca ativou."""
    escola = await criar_escola_e_gestor(client, "doc-solicitacao-inativa")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)
    # Propositadamente NÃO chama _ativar_preco — nenhum tipo está ativo.

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.post("/api/v1/documentos/solicitacoes", headers=headers_responsavel, json={
        "tipo_documento": "CERTIFICADO", "formato_entrega": "DIGITAL"
    })
    assert resp.status_code == 400, resp.text
    assert "não está disponível" in resp.json()["detail"]


async def test_criar_solicitacao_tipo_invalido_e_rejeitada(client):
    escola = await criar_escola_e_gestor(client, "doc-solicitacao-tipo-invalido")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.post("/api/v1/documentos/solicitacoes", headers=headers_responsavel, json={
        "tipo_documento": "PASSAPORTE", "formato_entrega": "DIGITAL"
    })
    assert resp.status_code == 400, resp.text
    assert "inválido" in resp.json()["detail"]


async def test_criar_solicitacao_outro_sem_descricao_e_rejeitada(client):
    escola = await criar_escola_e_gestor(client, "doc-solicitacao-outro-sem-descricao")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)
    await _ativar_preco(client, headers, "OUTRO")

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    headers_responsavel = auth_headers(resp.json()["access_token"])

    resp = await client.post("/api/v1/documentos/solicitacoes", headers=headers_responsavel, json={
        "tipo_documento": "OUTRO", "formato_entrega": "DIGITAL"
    })
    assert resp.status_code == 400, resp.text
    assert "Descreva o documento" in resp.json()["detail"]


async def test_criar_solicitacao_isolada_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "doc-solicitacao-iso-a")
    escola_b = await criar_escola_e_gestor(client, "doc-solicitacao-iso-b")
    headers_a = auth_headers(escola_a["token"])
    dados_a = await _criar_aluno_matriculado_com_portal(client, headers_a, date.today().year)
    await _ativar_preco(client, headers_a, "DECLARACAO")

    resp = await client.get("/api/v1/documentos/solicitacoes", headers=auth_headers(escola_b["token"]))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0
