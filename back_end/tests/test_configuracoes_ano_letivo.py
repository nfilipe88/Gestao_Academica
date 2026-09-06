"""Ano Letivo em Configurações — regra geral, início num ano e fim no
seguinte (ex.: setembro de 2026 a junho de 2027). Ver
app/schemas/configuracoes.py::ConfiguracaoTenantUpdate para a validação
de intervalo e app/database/models.py::Tenant para os campos. Módulo
novo, sem nenhum teste antes desta sessão (não existia campo nenhum de
ano letivo em Configurações)."""
from tests.conftest import auth_headers, criar_escola_e_gestor


def _payload_base(**overrides) -> dict:
    """PUT /configuracoes exige moeda (sem default) — mesmo payload
    mínimo em todos os testes, só o Ano Letivo varia."""
    base = {"moeda": "EUR"}
    base.update(overrides)
    return base


async def test_guardar_ano_letivo_completo_e_devolvido_no_get(client):
    escola = await criar_escola_e_gestor(client, "ano-letivo-completo")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/configuracoes", headers=headers, json=_payload_base(
        data_inicio_ano_letivo="2026-09-01", data_fim_ano_letivo="2027-06-30", ano_letivo_atual=2026,
    ))
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["data_inicio_ano_letivo"] == "2026-09-01"
    assert corpo["data_fim_ano_letivo"] == "2027-06-30"
    assert corpo["ano_letivo_atual"] == 2026

    resp = await client.get("/api/v1/configuracoes", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["data_inicio_ano_letivo"] == "2026-09-01"
    assert corpo["ano_letivo_atual"] == 2026


async def test_fim_igual_ou_anterior_ao_inicio_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "ano-letivo-invalido")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/configuracoes", headers=headers, json=_payload_base(
        data_inicio_ano_letivo="2026-09-01", data_fim_ano_letivo="2026-09-01",
    ))
    assert resp.status_code == 422, resp.text

    resp = await client.put("/api/v1/configuracoes", headers=headers, json=_payload_base(
        data_inicio_ano_letivo="2027-06-30", data_fim_ano_letivo="2026-09-01",
    ))
    assert resp.status_code == 422, resp.text


async def test_ano_letivo_por_preencher_nao_bloqueia_guardar_outros_campos(client):
    """Uma escola a meio de preencher (só uma das duas datas, ou
    nenhuma) continua a conseguir guardar o resto de Configurações —
    a exigência de completar isto é do frontend (guard de
    redirecionamento), nunca uma restrição da própria API."""
    escola = await criar_escola_e_gestor(client, "ano-letivo-parcial")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/configuracoes", headers=headers, json=_payload_base(
        iban="PT50000000000000000000000", data_inicio_ano_letivo="2026-09-01",
    ))
    assert resp.status_code == 200, resp.text
    assert resp.json()["data_fim_ano_letivo"] is None

    resp = await client.get("/api/v1/configuracoes", headers=headers)
    assert resp.json()["ano_letivo_atual"] is None


async def test_escola_nova_comeca_sem_ano_letivo_definido(client):
    escola = await criar_escola_e_gestor(client, "ano-letivo-por-omissao")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/configuracoes", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["data_inicio_ano_letivo"] is None
    assert corpo["data_fim_ano_letivo"] is None
    assert corpo["ano_letivo_atual"] is None
