"""Transferência de aluno entre escolas da plataforma — ver
app/cruds/transferencias.py. Não havia nenhum teste próprio deste
módulo; a cobertura aqui é focada no que foi acrescentado (notificar a
escola de destino ao concluir), não uma reescrita completa do fluxo."""
from datetime import date

from app.database.models import Tenant, Usuario
from app.database.session import AsyncSessionLocalSistema
from app.core.security import gerar_hash_senha
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _criar_super_admin(client) -> str:
    """Bootstrap direto (não há via de API) — mesmo padrão usado em
    tests/test_planos_por_aluno_modulo.py."""
    suf = sufixo_unico()
    email = f"superadmin.transf.{suf}@teste.pt"
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
    return resp.json()["access_token"]


async def test_transferencia_concluida_notifica_escola_destino(client):
    escola_a = await criar_escola_e_gestor(client, "transf-origem")
    escola_b = await criar_escola_e_gestor(client, "transf-destino")
    headers_a = auth_headers(escola_a["token"])

    resp = await client.post("/api/v1/alunos", headers=headers_a, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": "Aluno Transferido", "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]

    resp = await client.post("/api/v1/academico/cursos", headers=headers_a, json={"nome": "Curso"})
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", headers=headers_a, json={"curso_id": curso_id, "nome": "Série"})
    serie_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/turmas", headers=headers_a, json={
        "serie_ano_id": serie_id, "nome_codigo": "Turma A", "ano_letivo": date.today().year, "vagas_maximas": 30
    })
    turma_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers_a,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": date.today().year})
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Mudança de área"
    })
    assert resp.status_code == 200, resp.text
    solicitacao_id = resp.json()["id"]

    token_super_admin = await _criar_super_admin(client)
    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/aprovar", headers=auth_headers(token_super_admin))
    assert resp.status_code == 200, resp.text

    # A Secretaria/Gestor da escola B recebe o aluno sem matrícula — é
    # notificada de que falta concluir, não fica a descobrir por acaso.
    resp = await client.get("/api/v1/notificacoes", headers=auth_headers(escola_b["token"]))
    assert resp.status_code == 200, resp.text
    notificacoes = resp.json()
    assert any(
        n["tipo"] == "SOLICITACAO_TRANSFERENCIA" and "falta matricular" in n["titulo"].lower()
        for n in notificacoes
    ), f"a Secretaria da escola B devia ter sido notificada; recebeu: {notificacoes}"
