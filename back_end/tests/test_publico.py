"""Endpoints do site público (Preços) — ver app/api/v1/publico.py."""
from app.database.models import Tenant, Usuario
from app.database.session import AsyncSessionLocalSistema
from app.core.security import gerar_hash_senha
from tests.conftest import sufixo_unico


async def _criar_super_admin(client) -> dict:
    suf = sufixo_unico()
    email = f"superadmin.publico.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    async with AsyncSessionLocalSistema() as db:
        tenant_plataforma = Tenant(nome_fantasia=f"Plataforma Publico {suf}", nif=f"plat{suf}", status="ATIVO")
        db.add(tenant_plataforma)
        await db.flush()
        db.add(Usuario(
            tenant_id=tenant_plataforma.id, nome_completo="Super Admin Publico",
            email=email, senha_hash=gerar_hash_senha(senha), perfil_acesso="SUPER_ADMIN",
        ))
        await db.commit()
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return {"token": resp.json()["access_token"]}


async def test_listar_planos_publicos_nao_exige_autenticacao(client):
    resp = await client.get("/api/v1/public/planos")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


async def test_planos_publicos_so_mostram_ativos_e_sem_campos_internos(client):
    admin = await _criar_super_admin(client)
    headers = {"Authorization": f"Bearer {admin['token']}"}
    nome_ativo = f"Plano Publico Ativo {sufixo_unico()}"
    nome_inativo = f"Plano Publico Inativo {sufixo_unico()}"

    resp = await client.post("/api/v1/admin/planos", headers=headers, json={
        "nome": nome_ativo, "preco_por_aluno": "750.00", "descricao": "Plano de demonstração", "modulos": []
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/admin/planos", headers=headers, json={
        "nome": nome_inativo, "preco_por_aluno": "999.00", "modulos": []
    })
    plano_id = resp.json()["id"]
    resp = await client.patch(f"/api/v1/admin/planos/{plano_id}", headers=headers, json={
        "nome": nome_inativo, "preco_por_aluno": "999.00", "ativo": False, "modulos": []
    })
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/v1/public/planos")
    assert resp.status_code == 200, resp.text
    nomes = [p["nome"] for p in resp.json()]
    assert nome_ativo in nomes
    assert nome_inativo not in nomes

    plano_publico = next(p for p in resp.json() if p["nome"] == nome_ativo)
    assert "ativo" not in plano_publico
    assert plano_publico["descricao"] == "Plano de demonstração"
