"""Sistema de tickets de suporte — ver app/cruds/suporte.py e
app/api/v1/{suporte,publico,admin}.py. O chat de IA (Suporte Virtual)
não é testado aqui, mesma decisão já tomada para o Prof. Virtual
(app/core/prof_virtual.py, também sem testes) — evita chamadas reais e
pagas à API da Anthropic na suite; verificado manualmente no browser.
"""
from app.database.models import Tenant, Usuario
from app.database.session import AsyncSessionLocalSistema
from app.core.security import gerar_hash_senha
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _criar_super_admin(client) -> dict:
    suf = sufixo_unico()
    email = f"superadmin.suporte.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    async with AsyncSessionLocalSistema() as db:
        tenant_plataforma = Tenant(nome_fantasia=f"Plataforma Suporte {suf}", nif=f"plat{suf}", status="ATIVO")
        db.add(tenant_plataforma)
        await db.flush()
        db.add(Usuario(
            tenant_id=tenant_plataforma.id, nome_completo="Super Admin Suporte",
            email=email, senha_hash=gerar_hash_senha(senha), perfil_acesso="SUPER_ADMIN",
        ))
        await db.commit()
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return {"token": resp.json()["access_token"]}


async def test_visitante_cria_ticket_sem_sessao(client):
    resp = await client.post("/api/v1/public/tickets", json={
        "nome": "Encarregado Interessado", "email": "interessado@teste.pt",
        "assunto": "Dúvida sobre preços", "mensagem": "Quanto custa para 200 alunos?"
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"]


async def test_gestor_cria_e_le_o_proprio_ticket(client):
    escola = await criar_escola_e_gestor(client, "suporte-gestor")
    headers = auth_headers(escola["token"])

    resp = await client.post("/api/v1/suporte", headers=headers, json={
        "nome": "Gestor suporte-gestor", "email": escola["email"],
        "assunto": "Erro ao gerar recibo", "mensagem": "O PDF do recibo não abre."
    })
    assert resp.status_code == 201, resp.text
    ticket_id = resp.json()["id"]

    resp = await client.get("/api/v1/suporte", headers=headers)
    assert resp.status_code == 200, resp.text
    assert any(t["id"] == ticket_id for t in resp.json()["items"])

    resp = await client.get(f"/api/v1/suporte/{ticket_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["estado"] == "ABERTO"
    assert len(corpo["mensagens"]) == 1
    assert corpo["mensagens"][0]["autor_tipo"] == "CLIENTE"


async def test_escola_nao_ve_ticket_de_outra_escola(client):
    escola_a = await criar_escola_e_gestor(client, "suporte-iso-a")
    escola_b = await criar_escola_e_gestor(client, "suporte-iso-b")

    resp = await client.post("/api/v1/suporte", headers=auth_headers(escola_a["token"]), json={
        "nome": "A", "email": escola_a["email"], "assunto": "Só da escola A", "mensagem": "..."
    })
    ticket_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/suporte/{ticket_id}", headers=auth_headers(escola_b["token"]))
    assert resp.status_code == 404

    resp = await client.get("/api/v1/suporte", headers=auth_headers(escola_b["token"]))
    assert all(t["id"] != ticket_id for t in resp.json()["items"])


async def test_secretaria_tambem_pode_aceder_ao_suporte(client):
    """Suporte é GESTOR + SECRETARIA (exigir_perfil em api/v1/suporte.py),
    mesmo alcance de /usuarios/auditoria — não é restrito só ao Gestor."""
    escola = await criar_escola_e_gestor(client, "suporte-rbac")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers, json={
        "nome_completo": "Secretaria Suporte", "email": f"sec.suporte.{escola['nif']}@teste.pt", "palavra_passe": "SenhaTeste123!"
    })
    assert resp.status_code == 201, resp.text
    resp_login = await client.post("/api/v1/auth/login", data={
        "username": f"sec.suporte.{escola['nif']}@teste.pt", "password": "SenhaTeste123!"
    })
    headers_secretaria = auth_headers(resp_login.json()["access_token"])

    resp = await client.get("/api/v1/suporte", headers=headers_secretaria)
    assert resp.status_code == 200, "Secretaria deve poder aceder ao Suporte, mesmo alcance de /usuarios/auditoria"


async def test_cliente_reabre_ticket_resolvido_ao_responder(client):
    escola = await criar_escola_e_gestor(client, "suporte-reabrir")
    headers = auth_headers(escola["token"])
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["token"])

    resp = await client.post("/api/v1/suporte", headers=headers, json={
        "nome": "Gestor", "email": escola["email"], "assunto": "Pergunta", "mensagem": "..."
    })
    ticket_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/admin/tickets/{ticket_id}/estado", headers=headers_admin, json={"estado": "RESOLVIDO"})
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"/api/v1/suporte/{ticket_id}/mensagens", headers=headers, json={"corpo": "Continua a acontecer."})
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/suporte/{ticket_id}", headers=headers)
    assert resp.json()["estado"] == "EM_ANDAMENTO"
    assert len(resp.json()["mensagens"]) == 2


async def test_admin_ve_e_responde_tickets_de_qualquer_origem(client):
    escola = await criar_escola_e_gestor(client, "suporte-admin")
    admin = await _criar_super_admin(client)
    headers_admin = auth_headers(admin["token"])

    resp = await client.post("/api/v1/public/tickets", json={
        "nome": "Visitante", "email": "visitante.admin@teste.pt", "assunto": "Pergunta pública", "mensagem": "..."
    })
    ticket_publico_id = resp.json()["id"]

    resp = await client.post("/api/v1/suporte", headers=auth_headers(escola["token"]), json={
        "nome": "Gestor", "email": escola["email"], "assunto": "Pergunta da escola", "mensagem": "..."
    })
    ticket_escola_id = resp.json()["id"]

    resp = await client.get("/api/v1/admin/tickets", headers=headers_admin, params={"page_size": 100})
    assert resp.status_code == 200, resp.text
    ids = [t["id"] for t in resp.json()["items"]]
    assert ticket_publico_id in ids and ticket_escola_id in ids
    ticket_publico = next(t for t in resp.json()["items"] if t["id"] == ticket_publico_id)
    ticket_escola = next(t for t in resp.json()["items"] if t["id"] == ticket_escola_id)
    assert ticket_publico["nome_escola"] is None
    assert ticket_escola["nome_escola"] is not None

    resp = await client.post(f"/api/v1/admin/tickets/{ticket_publico_id}/mensagens", headers=headers_admin, json={"corpo": "Resposta da equipa."})
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/admin/tickets/{ticket_publico_id}", headers=headers_admin)
    assert len(resp.json()["mensagens"]) == 2
    assert resp.json()["mensagens"][1]["autor_tipo"] == "SUPORTE"
    assert resp.json()["estado"] == "EM_ANDAMENTO"


async def test_admin_e_o_unico_que_gere_tickets(client):
    escola = await criar_escola_e_gestor(client, "suporte-admin-rbac")
    resp = await client.get("/api/v1/admin/tickets", headers=auth_headers(escola["token"]))
    assert resp.status_code == 403
