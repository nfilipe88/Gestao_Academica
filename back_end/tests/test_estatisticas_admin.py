"""Estatísticas para o Super Admin — as mesmas do Gestor
(app/api/v1/estatisticas.py), só que cross-tenant: o Super Admin
escolhe a escola pelo tenant_id do path (ver app/api/v1/admin.py).
Reaproveita os mesmos cruds (obter_dashboard/obter_relatorio,
criar_despesa/listar_despesas/remover_despesa) — o único que muda é
quem chama e de onde vem o tenant_id, por isso os testes aqui só
confirmam que a rota cross-tenant devolve os mesmos dados da rota do
Gestor, mais o isolamento/RBAC próprios do Painel Super Admin."""
import io
from datetime import date

import openpyxl

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_estatisticas import _montar_cenario
from tests.test_planos_por_aluno_modulo import _criar_super_admin


async def test_dashboard_do_tenant_pelo_super_admin(client):
    escola = await criar_escola_e_gestor(client, "estatisticas-admin-dashboard")
    headers_escola = auth_headers(escola["token"])
    await _montar_cenario(client, headers_escola)

    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])

    resp = await client.get(f"/api/v1/admin/tenants/{escola['tenant_id']}/estatisticas/dashboard", headers=headers_admin)
    assert resp.status_code == 200, resp.text
    dados = resp.json()
    assert dados["total_alunos_matriculados"] == 5
    faixas = {f["faixa"]: f["total"] for f in dados["faixas_etarias"]}
    assert faixas == {"5-9": 1, "10-14": 2, "15-18": 1, "19+": 1}


async def test_relatorio_do_tenant_pelo_super_admin_inclui_financeiro(client):
    escola = await criar_escola_e_gestor(client, "estatisticas-admin-relatorio")
    headers_escola = auth_headers(escola["token"])
    await _montar_cenario(client, headers_escola)
    hoje = date.today()

    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])

    resp = await client.get(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/estatisticas/relatorio?data_inicio={hoje}&data_fim={hoje}",
        headers=headers_admin
    )
    assert resp.status_code == 200, resp.text
    dados = resp.json()
    assert float(dados["total_entradas_periodo"]) == 100.0
    assert float(dados["total_saidas_periodo"]) == 300.0
    assert float(dados["saldo_periodo"]) == -200.0


async def test_estatisticas_admin_isoladas_por_tenant_escolhido(client):
    """Escolher a escola A não pode devolver dados da escola B, mesmo
    ambas existindo na mesma plataforma."""
    escola_a = await criar_escola_e_gestor(client, "estatisticas-admin-iso-a")
    escola_b = await criar_escola_e_gestor(client, "estatisticas-admin-iso-b")
    await _montar_cenario(client, auth_headers(escola_a["token"]))

    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])

    resp = await client.get(f"/api/v1/admin/tenants/{escola_b['tenant_id']}/estatisticas/dashboard", headers=headers_admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_alunos_matriculados"] == 0

    resp = await client.get(f"/api/v1/admin/tenants/{escola_a['tenant_id']}/estatisticas/dashboard", headers=headers_admin)
    assert resp.json()["total_alunos_matriculados"] == 5


async def test_estatisticas_admin_bloqueada_para_gestor(client):
    """As rotas cross-tenant de /admin são exclusivas do Super Admin —
    um Gestor autenticado (mesmo dono da própria escola) é recusado."""
    escola = await criar_escola_e_gestor(client, "estatisticas-admin-rbac-gestor")
    headers_escola = auth_headers(escola["token"])

    resp = await client.get(f"/api/v1/admin/tenants/{escola['tenant_id']}/estatisticas/dashboard", headers=headers_escola)
    assert resp.status_code == 403


async def test_despesa_do_tenant_pelo_super_admin_criar_listar_remover(client):
    escola = await criar_escola_e_gestor(client, "estatisticas-admin-despesas")
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    hoje = date.today()

    resp = await client.post(f"/api/v1/admin/tenants/{escola['tenant_id']}/despesas", headers=headers_admin, json={
        "categoria": "MATERIAL", "descricao": "Material didático", "valor": "150.00", "data_despesa": str(hoje)
    })
    assert resp.status_code == 201, resp.text
    despesa_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/admin/tenants/{escola['tenant_id']}/despesas", headers=headers_admin)
    assert resp.status_code == 200, resp.text
    itens = resp.json()["items"]
    assert len(itens) == 1
    assert itens[0]["categoria"] == "MATERIAL"

    # A escola vê a mesma despesa pela sua própria rota — confirma que
    # é a mesma tabela, só a via de acesso muda.
    resp = await client.get("/api/v1/financeiro/despesas", headers=auth_headers(escola["token"]))
    assert resp.json()["items"][0]["id"] == despesa_id

    resp = await client.delete(f"/api/v1/admin/tenants/{escola['tenant_id']}/despesas/{despesa_id}", headers=headers_admin)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/admin/tenants/{escola['tenant_id']}/despesas", headers=headers_admin)
    assert resp.json()["items"] == []


async def test_exportar_relatorio_xlsx_do_tenant_pelo_super_admin(client):
    escola = await criar_escola_e_gestor(client, "estatisticas-admin-xlsx")
    await _montar_cenario(client, auth_headers(escola["token"]))
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    hoje = date.today()

    resp = await client.get(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/estatisticas/relatorio.xlsx?data_inicio={hoje}&data_fim={hoje}",
        headers=headers_admin
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    livro = openpyxl.load_workbook(io.BytesIO(resp.content))
    assert "Resumo" in livro.sheetnames


async def test_exportar_relatorio_xls_do_tenant_pelo_super_admin(client):
    escola = await criar_escola_e_gestor(client, "estatisticas-admin-xls")
    await _montar_cenario(client, auth_headers(escola["token"]))
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    hoje = date.today()

    resp = await client.get(
        f"/api/v1/admin/tenants/{escola['tenant_id']}/estatisticas/relatorio.xls?data_inicio={hoje}&data_fim={hoje}",
        headers=headers_admin
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/vnd.ms-excel"
    assert resp.content.startswith(b"\xd0\xcf\x11\xe0")
