"""Despesas (saídas financeiras) — ver app/cruds/financeiro.py. Nova
tabela, introduzida como pré-requisito das estatísticas financeiras
(ver test_estatisticas.py) — sem isto, "maiores saídas" não tinha
nenhum dado real na plataforma."""
from datetime import date, timedelta

from tests.conftest import auth_headers, criar_escola_e_gestor


async def test_criar_e_listar_despesa(client):
    escola = await criar_escola_e_gestor(client, "despesas-basico")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "SALARIOS", "descricao": "Salário do corpo docente — agosto",
        "valor": "50000.00", "data_despesa": str(date.today()), "forma_pagamento": "TRANSFERENCIA"
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["categoria"] == "SALARIOS"
    assert float(resp.json()["valor"]) == 50000.00

    resp = await client.get("/api/v1/financeiro/despesas", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


async def test_despesa_categoria_invalida_e_rejeitada(client):
    escola = await criar_escola_e_gestor(client, "despesas-categoria-invalida")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "VIAGENS", "descricao": "X", "valor": "100.00", "data_despesa": str(date.today())
    })
    assert resp.status_code == 422, resp.text


async def test_despesa_valor_zero_e_rejeitada(client):
    escola = await criar_escola_e_gestor(client, "despesas-valor-zero")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "OUTRO", "descricao": "X", "valor": "0", "data_despesa": str(date.today())
    })
    assert resp.status_code == 422, resp.text


async def test_despesa_descricao_vazia_e_rejeitada(client):
    escola = await criar_escola_e_gestor(client, "despesas-descricao-vazia")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "OUTRO", "descricao": "   ", "valor": "10.00", "data_despesa": str(date.today())
    })
    assert resp.status_code == 422, resp.text


async def test_listar_despesas_filtra_por_data_e_categoria(client):
    escola = await criar_escola_e_gestor(client, "despesas-filtros")
    headers = auth_headers(escola["token"])
    hoje = date.today()

    await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "RENDA", "descricao": "Renda de agosto", "valor": "1000.00", "data_despesa": str(hoje)
    })
    await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "MATERIAL", "descricao": "Material de escritório", "valor": "200.00",
        "data_despesa": str(hoje - timedelta(days=60))
    })

    resp = await client.get(
        f"/api/v1/financeiro/despesas?data_inicio={hoje - timedelta(days=5)}&data_fim={hoje}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["categoria"] == "RENDA"

    resp = await client.get("/api/v1/financeiro/despesas?categoria=MATERIAL", headers=headers)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["categoria"] == "MATERIAL"


async def test_remover_despesa(client):
    escola = await criar_escola_e_gestor(client, "despesas-remover")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/financeiro/despesas", headers=headers, json={
        "categoria": "OUTRO", "descricao": "Para apagar", "valor": "10.00", "data_despesa": str(date.today())
    })
    despesa_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/financeiro/despesas/{despesa_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    resp = await client.get("/api/v1/financeiro/despesas", headers=headers)
    assert resp.json()["total"] == 0


async def test_remover_despesa_inexistente_e_404(client):
    escola = await criar_escola_e_gestor(client, "despesas-remover-404")
    headers = auth_headers(escola["token"])

    resp = await client.delete(
        "/api/v1/financeiro/despesas/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert resp.status_code == 404, resp.text


async def test_despesa_professor_nao_pode_criar_nem_listar(client):
    from tests.test_comportamento import _criar_professor_com_token
    escola = await criar_escola_e_gestor(client, "despesas-rbac-professor")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Despesas")
    headers_professor = auth_headers(token_professor)

    resp = await client.post("/api/v1/financeiro/despesas", headers=headers_professor, json={
        "categoria": "OUTRO", "descricao": "Não devia entrar", "valor": "10.00", "data_despesa": str(date.today())
    })
    assert resp.status_code == 403, resp.text

    resp = await client.get("/api/v1/financeiro/despesas", headers=headers_professor)
    assert resp.status_code == 403, resp.text


async def test_despesas_isoladas_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "despesas-iso-a")
    escola_b = await criar_escola_e_gestor(client, "despesas-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])

    await client.post("/api/v1/financeiro/despesas", headers=headers_a, json={
        "categoria": "OUTRO", "descricao": "Só da escola A", "valor": "10.00", "data_despesa": str(date.today())
    })

    resp = await client.get("/api/v1/financeiro/despesas", headers=headers_b)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0
