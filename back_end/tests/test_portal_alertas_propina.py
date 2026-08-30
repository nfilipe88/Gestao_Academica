"""Alertas de propina em atraso no Portal — além do e-mail/SMS que a
régua de cobrança (RN04) já enviava, o aluno e o responsável (que pode
representar vários educandos) passam a ver isto também dentro da
própria plataforma. Ver app/cruds/financeiro.py::processar_regua_cobranca_do_tenant
e app/cruds/portal.py::listar_meus_educandos."""
from datetime import date, timedelta

from sqlalchemy import select

from app.database.models_financeiro import FaturaMensalidade
from app.database.session import AsyncSessionLocalSistema
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _preparar_aluno_com_fatura_em_atraso(client, headers) -> dict:
    """Curso -> Turma -> Aluno -> Responsável (ambos com acesso ao
    Portal) -> Matrícula -> Contrato -> uma fatura manualmente
    atrasada 5 dias (a régua não controla a data de vencimento pela
    API, só pelo dia_vencimento_padrao do contrato — para testar o
    aviso de atraso sem esperar dias a sério, ajusta-se a data
    diretamente na base)."""
    ano_letivo = date.today().year
    suf = sufixo_unico()

    resp = await client.post("/api/v1/academico/cursos", json={"nome": "Curso"}, headers=headers)
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", json={"curso_id": curso_id, "nome": "Série"}, headers=headers)
    serie_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/turmas", headers=headers, json={
        "serie_ano_id": serie_id, "nome_codigo": "Turma A", "ano_letivo": ano_letivo, "vagas_maximas": 30
    })
    turma_id = resp.json()["id"]

    email_aluno = f"aluno.portal.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{suf}", "nome_completo": "Aluno Portal", "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/alunos/{aluno_id}/criar-acesso", headers=headers,
                              json={"email": email_aluno, "palavra_passe": senha})
    assert resp.status_code == 201, resp.text

    email_responsavel = f"responsavel.portal.{suf}@teste.pt"
    resp = await client.post("/api/v1/responsaveis", headers=headers,
                              json={"nome_completo": "Responsável Portal", "telefone_contato": "+244900000000"})
    responsavel_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/responsaveis/{responsavel_id}/criar-acesso", headers=headers,
                              json={"email": email_responsavel, "palavra_passe": senha})
    assert resp.status_code == 201, resp.text
    await client.post(f"/api/v1/alunos/{aluno_id}/responsaveis", headers=headers,
                       json={"responsavel_id": responsavel_id, "tipo_parentesco": "Mãe", "responsavel_financeiro": True})

    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo})
    matricula_id = resp.json()["id"]
    resp = await client.post("/api/v1/financeiro/contratos", headers=headers, json={
        "matricula_id": matricula_id, "responsavel_id": responsavel_id,
        "valor_total_anual": "1200.00", "quantidade_parcelas": 12,
    })
    contrato_id = resp.json()["id"]
    resp = await client.get(f"/api/v1/financeiro/contratos/{contrato_id}/faturas", headers=headers)
    primeira_fatura_id = resp.json()[0]["id"]

    async with AsyncSessionLocalSistema() as db:
        fatura = (await db.execute(select(FaturaMensalidade).where(FaturaMensalidade.id == primeira_fatura_id))).scalars().first()
        fatura.data_vencimento = date.today() - timedelta(days=5)
        await db.commit()

    return {
        "aluno_id": aluno_id, "email_aluno": email_aluno, "email_responsavel": email_responsavel, "senha": senha,
    }


async def _login(client, email: str, senha: str) -> str:
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def test_regua_cobranca_notifica_aluno_e_responsavel_no_portal(client):
    escola = await criar_escola_e_gestor(client, "portal-alerta")
    headers = auth_headers(escola["token"])
    dados = await _preparar_aluno_com_fatura_em_atraso(client, headers)

    resp = await client.post("/api/v1/financeiro/regua-cobranca/processar", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["emails_enviados"]["aviso_atraso"] == 1

    for email in (dados["email_aluno"], dados["email_responsavel"]):
        token = await _login(client, email, dados["senha"])
        resp = await client.get("/api/v1/notificacoes", headers=auth_headers(token))
        assert resp.status_code == 200, resp.text
        notificacoes = resp.json()
        assert any(n["tipo"] == "PROPINA" for n in notificacoes), f"{email} devia ter recebido a notificação PROPINA"


async def test_meus_educandos_mostra_propina_em_atraso(client):
    escola = await criar_escola_e_gestor(client, "portal-educandos-atraso")
    headers = auth_headers(escola["token"])
    dados = await _preparar_aluno_com_fatura_em_atraso(client, headers)

    token_responsavel = await _login(client, dados["email_responsavel"], dados["senha"])
    resp = await client.get("/api/v1/portal/meus-educandos", headers=auth_headers(token_responsavel))
    assert resp.status_code == 200, resp.text
    educandos = resp.json()
    assert len(educandos) == 1
    assert educandos[0]["tem_propina_em_atraso"] is True
