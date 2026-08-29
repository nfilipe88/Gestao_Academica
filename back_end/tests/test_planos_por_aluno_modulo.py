"""
Planos SaaS por aluno + módulo: o Super Admin passa a definir quanto
cobrar por aluno cadastrado (substitui a antiga mensalidade fixa) e
quais módulos da plataforma entram no plano, cada um com o seu preço
adicional — um módulo AUSENTE do plano fica mesmo bloqueado (403), não
é só uma questão de faturação (ver app/core/modulos.py).
"""
from datetime import date, timedelta

from sqlalchemy import select

from app.database.models import Tenant, Usuario
from app.database.session import AsyncSessionLocalSistema
from app.core.security import gerar_hash_senha
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _criar_super_admin(client) -> dict:
    """Não há via de API para isto (é deliberadamente um bootstrap, não
    um endpoint normal — ver seed_super_admin.py) — insere diretamente,
    com um tenant "plataforma" e sufixo próprios, para não colidir com
    outros testes a correr em paralelo nem com um super admin já
    semeado manualmente."""
    suf = sufixo_unico()
    email = f"superadmin.teste.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    async with AsyncSessionLocalSistema() as db:
        tenant_plataforma = Tenant(nome_fantasia=f"Plataforma Teste {suf}", nif=f"plat{suf}", status="ATIVO")
        db.add(tenant_plataforma)
        await db.flush()
        db.add(Usuario(
            tenant_id=tenant_plataforma.id, nome_completo="Super Admin Teste",
            email=email, senha_hash=gerar_hash_senha(senha), perfil_acesso="SUPER_ADMIN",
        ))
        await db.commit()

    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _criar_plano(client, headers_admin, preco_por_aluno: str, modulos: list[dict] | None = None) -> str:
    resp = await client.post("/api/v1/admin/planos", headers=headers_admin, json={
        "nome": f"Plano Teste {sufixo_unico()}", "preco_por_aluno": preco_por_aluno,
        "modulos": modulos or [],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_criar_plano_com_preco_por_aluno_e_modulos(client):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])

    plano_id = await _criar_plano(client, headers_admin, "500.00", modulos=[
        {"modulo": "Financeiro", "preco_adicional": "0.00"},
        {"modulo": "CRM", "preco_adicional": "10000.00"},
    ])

    resp = await client.get("/api/v1/admin/planos", headers=headers_admin)
    assert resp.status_code == 200
    plano = next(p for p in resp.json() if p["id"] == plano_id)
    assert plano["preco_por_aluno"] == 500.0
    nomes_modulos = {m["modulo"] for m in plano["modulos"]}
    assert nomes_modulos == {"Financeiro", "CRM"}


async def test_criar_plano_com_modulo_invalido_e_rejeitado(client):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])

    resp = await client.post("/api/v1/admin/planos", headers=headers_admin, json={
        "nome": f"Plano Inválido {sufixo_unico()}", "preco_por_aluno": "100.00",
        "modulos": [{"modulo": "Módulo Que Não Existe", "preco_adicional": "0"}],
    })
    assert resp.status_code == 422


async def test_mensalidade_da_assinatura_e_preco_por_aluno_vezes_contagem_mais_modulos(client):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    escola = await criar_escola_e_gestor(client, "mensalidade")
    headers_escola = auth_headers(escola["token"])

    # 3 alunos cadastrados na escola.
    for i in range(3):
        await client.post("/api/v1/alunos", json={
            "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": f"Aluno Mensalidade {i}", "data_nascimento": "2015-01-01",
        }, headers=headers_escola)

    plano_id = await _criar_plano(client, headers_admin, "500.00", modulos=[
        {"modulo": "Financeiro", "preco_adicional": "2000.00"},
    ])
    resp = await client.put(f"/api/v1/admin/tenants/{escola['tenant_id']}/assinatura", headers=headers_admin, json={
        "plano_id": plano_id, "proxima_cobranca": (date.today() + timedelta(days=30)).isoformat(),
    })
    assert resp.status_code == 200, resp.text
    assinatura = resp.json()
    assert assinatura["total_alunos"] == 3
    # 500.00 * 3 + 2000.00 = 3500.00
    assert assinatura["mensalidade"] == 3500.0


async def test_modulo_nao_incluido_no_plano_bloqueia_acesso(client):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    escola = await criar_escola_e_gestor(client, "gate")
    headers_escola = auth_headers(escola["token"])

    # Plano só com Financeiro — CRM fica de fora.
    plano_id = await _criar_plano(client, headers_admin, "500.00", modulos=[{"modulo": "Financeiro", "preco_adicional": "0"}])
    resp = await client.put(f"/api/v1/admin/tenants/{escola['tenant_id']}/assinatura", headers=headers_admin, json={
        "plano_id": plano_id, "proxima_cobranca": (date.today() + timedelta(days=30)).isoformat(),
    })
    assert resp.status_code == 200, resp.text

    # Financeiro está incluído — acede normalmente (404 por a matrícula
    # não existir é esperado; o que importa é NÃO ser 403 do módulo).
    resp = await client.get(
        "/api/v1/financeiro/matriculas/00000000-0000-0000-0000-000000000000/responsaveis", headers=headers_escola
    )
    assert resp.status_code != 403

    # CRM não está incluído — bloqueado, mesmo sendo GESTOR (perfil certo, plano é que não inclui).
    resp = await client.get("/api/v1/crm/leads", headers=headers_escola)
    assert resp.status_code == 403
    assert "não está incluído no plano" in resp.json()["detail"]

    # Um módulo NUNCA gateável (Alunos) continua acessível na mesma.
    resp = await client.get("/api/v1/alunos?page=1&page_size=10", headers=headers_escola)
    assert resp.status_code == 200


async def test_tenant_sem_assinatura_tem_acesso_total_a_todos_os_modulos(client):
    """Falha aberta de propósito — uma escola sem plano atribuído ainda
    não pode ficar bloqueada (ver docstring de app/core/modulos.py)."""
    escola = await criar_escola_e_gestor(client, "sem-plano")
    headers_escola = auth_headers(escola["token"])

    resp = await client.get("/api/v1/crm/leads", headers=headers_escola)
    assert resp.status_code != 403


async def test_super_admin_nunca_e_bloqueado_por_modulo(client):
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["access_token"])
    # Super Admin nem tem assinatura própria — a rota /admin/planos já
    # não é gateada (é do próprio módulo de administração), mas outras
    # rotas gateadas (ex.: /crm) também nunca o bloqueiam.
    resp = await client.get("/api/v1/admin/tenants", headers=headers_admin)
    assert resp.status_code == 200
