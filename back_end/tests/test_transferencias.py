"""Transferência de aluno entre escolas da plataforma — ver
app/cruds/transferencias.py. Decisão direta entre instituições: quem
aprova/rejeita é o Gestor/Secretaria da escola de DESTINO, não o Super
Admin (que mantém só uma listagem de auditoria, GET /transferencias —
ver docstring de models_transferencias.py)."""
from datetime import date

from app.database.models import Tenant, Usuario
from app.database.session import AsyncSessionLocalSistema
from app.core.security import gerar_hash_senha
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _criar_super_admin(client) -> str:
    """Bootstrap direto (não há via de API) — mesmo padrão usado em
    tests/test_planos_por_aluno_modulo.py. Usado só para a listagem de
    auditoria e para confirmar que o Super Admin NÃO decide."""
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


async def _matricular_aluno_ativo(client, headers, nome: str) -> tuple[str, str]:
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/cursos", headers=headers, json={"nome": "Curso"})
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", headers=headers, json={"curso_id": curso_id, "nome": "Série"})
    serie_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/turmas", headers=headers, json={
        "serie_ano_id": serie_id, "nome_codigo": f"Turma {sufixo_unico()}", "ano_letivo": date.today().year, "vagas_maximas": 30
    })
    turma_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": date.today().year})
    assert resp.status_code == 201, resp.text
    return aluno_id, resp.json()["id"]


async def test_transferencia_concluida_pela_escola_destino(client):
    escola_a = await criar_escola_e_gestor(client, "transf-origem")
    escola_b = await criar_escola_e_gestor(client, "transf-destino")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    aluno_id, matricula_id = await _matricular_aluno_ativo(client, headers_a, "Aluno Transferido")

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Mudança de área"
    })
    assert resp.status_code == 200, resp.text
    solicitacao_id = resp.json()["id"]

    # Ao pedir, a matrícula de origem fica suspensa (EM_TRANSFERENCIA)
    # — não é mais "candidata" a nada normal enquanto o destino decide.
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers_a)
    assert resp.json()[0]["status_matricula"] == "EM_TRANSFERENCIA"

    # Aparece na caixa de entrada da escola B — não na da A nem na de
    # uma terceira escola qualquer.
    resp = await client.get("/api/v1/transferencias/recebidas", headers=headers_b)
    assert resp.status_code == 200, resp.text
    assert any(s["id"] == solicitacao_id for s in resp.json()["items"])
    resp = await client.get("/api/v1/transferencias/recebidas", headers=headers_a)
    assert not any(s["id"] == solicitacao_id for s in resp.json()["items"])

    # É a escola de DESTINO que decide — direto, sem Super Admin.
    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/aprovar", headers=headers_b)
    assert resp.status_code == 200, resp.text

    # A matrícula de origem fecha como TRANSFERIDO.
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers_a)
    assert resp.json()[0]["status_matricula"] == "TRANSFERIDO"

    # A Secretaria/Gestor da escola B recebe o aluno sem matrícula — é
    # notificada de que falta concluir, não fica a descobrir por acaso.
    resp = await client.get("/api/v1/notificacoes", headers=headers_b)
    assert resp.status_code == 200, resp.text
    notificacoes = resp.json()
    assert any(
        n["tipo"] == "SOLICITACAO_TRANSFERENCIA" and "falta matricular" in n["titulo"].lower()
        for n in notificacoes
    ), f"a Secretaria da escola B devia ter sido notificada; recebeu: {notificacoes}"


async def test_apenas_a_escola_de_destino_decide(client):
    """Nem a escola de origem, nem uma terceira escola qualquer, nem o
    Super Admin conseguem aprovar/rejeitar — só a de destino."""
    escola_a = await criar_escola_e_gestor(client, "transf-rbac-origem")
    escola_b = await criar_escola_e_gestor(client, "transf-rbac-destino")
    escola_c = await criar_escola_e_gestor(client, "transf-rbac-terceira")
    headers_a = auth_headers(escola_a["token"])
    aluno_id, _ = await _matricular_aluno_ativo(client, headers_a, "Aluno Rbac")

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "teste"
    })
    assert resp.status_code == 200, resp.text
    solicitacao_id = resp.json()["id"]

    # Origem: não é dirigido a ela.
    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/aprovar", headers=headers_a)
    assert resp.status_code == 403, resp.text

    # Escola terceira, nem sequer envolvida.
    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/aprovar", headers=auth_headers(escola_c["token"]))
    assert resp.status_code == 403, resp.text

    # Super Admin: já não decide, só audita.
    token_super_admin = await _criar_super_admin(client)
    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/aprovar", headers=auth_headers(token_super_admin))
    assert resp.status_code == 403, resp.text
    resp = await client.get("/api/v1/transferencias", headers=auth_headers(token_super_admin))
    assert resp.status_code == 200, resp.text
    assert any(s["id"] == solicitacao_id for s in resp.json()["items"]), "auditoria continua a ver o pedido"


async def test_rejeitar_devolve_matricula_de_origem_a_ativo(client):
    escola_a = await criar_escola_e_gestor(client, "transf-rejeitar-origem")
    escola_b = await criar_escola_e_gestor(client, "transf-rejeitar-destino")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    aluno_id, _ = await _matricular_aluno_ativo(client, headers_a, "Aluno Rejeitado")

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Mudança de área"
    })
    assert resp.status_code == 200, resp.text
    solicitacao_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers_a)
    assert resp.json()[0]["status_matricula"] == "EM_TRANSFERENCIA"

    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/rejeitar", headers=headers_b,
                               json={"observacoes": "Documentação insuficiente."})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJEITADA"

    # O aluno volta em ativo na escola de origem — não fica preso em
    # EM_TRANSFERENCIA por um pedido que já não vai a lado nenhum.
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers_a)
    assert resp.json()[0]["status_matricula"] == "ATIVO"

    # Decidido — um segundo pedido para o mesmo aluno já não colide com este.
    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Novo pedido, desta vez completo"
    })
    assert resp.status_code == 200, resp.text

    # Rejeitar um pedido já decidido não é aceite outra vez.
    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/rejeitar", headers=headers_b,
                               json={"observacoes": "segunda tentativa"})
    assert resp.status_code == 400, resp.text


async def test_reingresso_cross_escola_apos_fim_de_ciclo(client):
    """O aluno já tinha saído da escola A (Fim de Ciclo — CICLO_CONCLUIDO,
    ver app/cruds/matriculas.py) e só agora aparece a querer continuar
    noutra escola desta plataforma. Não é uma transferência "a quente"
    (não há matrícula ATIVO para suspender/fechar), mas o mesmo
    mecanismo de pedido/decisão da escola de destino serve — ver
    docstring de models_transferencias.py."""
    escola_a = await criar_escola_e_gestor(client, "reingresso-origem")
    escola_b = await criar_escola_e_gestor(client, "reingresso-destino")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])

    resp = await client.post("/api/v1/alunos", headers=headers_a, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": "Aluno Fim De Ciclo", "data_nascimento": "2010-05-10"
    })
    aluno_id = resp.json()["id"]

    resp = await client.post("/api/v1/academico/cursos", headers=headers_a, json={"nome": "Curso"})
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", headers=headers_a, json={"curso_id": curso_id, "nome": "Série"})
    serie_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/turmas", headers=headers_a, json={
        "serie_ano_id": serie_id, "nome_codigo": "9º Ano", "ano_letivo": date.today().year, "vagas_maximas": 30
    })
    turma_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers_a,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": date.today().year})
    assert resp.status_code == 201, resp.text
    matricula_id = resp.json()["id"]

    # Fim de Ciclo: a escola A não tem sequência para o ano seguinte.
    resp = await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers_a, json={
        "status_matricula": "CICLO_CONCLUIDO", "motivo": "CONCLUSAO_ESCOLARIDADE"
    })
    assert resp.status_code == 200, resp.text

    # Sem matrícula ATIVO, o pedido de transferência normal continua a
    # funcionar — é precisamente o caso que passou a ser aceite.
    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Escola A não tem 10º ano — reingresso na escola B"
    })
    assert resp.status_code == 200, resp.text
    solicitacao_id = resp.json()["id"]

    # CICLO_CONCLUIDO nunca é tocado, nem sequer suspenso, enquanto pendente.
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers_a)
    assert resp.json()[0]["status_matricula"] == "CICLO_CONCLUIDO"

    resp = await client.patch(f"/api/v1/transferencias/{solicitacao_id}/aprovar", headers=headers_b)
    assert resp.status_code == 200, resp.text
    aluno_novo_id = resp.json()["aluno_novo_id"]
    assert aluno_novo_id

    # A matrícula de origem continua CICLO_CONCLUIDO — nunca reescrita
    # para TRANSFERIDO (o Fim de Ciclo já tinha acontecido de facto).
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/matriculas", headers=headers_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["status_matricula"] == "CICLO_CONCLUIDO"

    # O Histórico Escolar (notas/anos da escola A) fica anexado
    # automaticamente ao aluno recém-criado na escola B — sem a família
    # ter de o pedir/pagar à parte.
    resp = await client.get(f"/api/v1/alunos/{aluno_novo_id}/documentos", headers=headers_b)
    assert resp.status_code == 200, resp.text
    documentos = resp.json()
    assert len(documentos) == 1
    assert "Histórico Escolar" in documentos[0]["descricao"]
    documento_id = documentos[0]["id"]

    resp = await client.get(f"/api/v1/alunos/{aluno_novo_id}/documentos/{documento_id}/url", headers=headers_b)
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:application/pdf;base64,")

    # A escola B é notificada com a redação de reingresso, não de transferência.
    resp = await client.get("/api/v1/notificacoes", headers=headers_b)
    assert resp.status_code == 200, resp.text
    notificacoes = resp.json()
    assert any(
        n["tipo"] == "SOLICITACAO_TRANSFERENCIA" and "reingressou" in n["titulo"].lower()
        for n in notificacoes
    ), f"a Secretaria da escola B devia ver a redação de reingresso; recebeu: {notificacoes}"


async def test_transferencia_recusada_para_aluno_sem_matricula_valida(client):
    """Um aluno TRANCADO (nem ativo nem em Fim de Ciclo) não é candidato
    nem a transferência a quente nem a reingresso cross-escola."""
    escola_a = await criar_escola_e_gestor(client, "transf-invalido")
    escola_b = await criar_escola_e_gestor(client, "transf-invalido-destino")
    headers_a = auth_headers(escola_a["token"])

    aluno_id, matricula_id = await _matricular_aluno_ativo(client, headers_a, "Aluno Trancado")
    resp = await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers_a,
                               json={"status_matricula": "TRANCADO"})
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "teste"
    })
    assert resp.status_code == 400, resp.text


async def test_pedido_de_transferencia_duplicado_e_rejeitado_a_quente(client):
    """Transferência "a quente" (ATIVO): a própria suspensão da
    matrícula (EM_TRANSFERENCIA, ver criar_solicitacao) já bloqueia um
    segundo pedido mais cedo — a matrícula deixa de estar num dos
    estados aceites antes sequer de chegar ao check de "já existe um
    pedido pendente" (que continua a existir para o caso de reingresso,
    ver o teste seguinte)."""
    escola_a = await criar_escola_e_gestor(client, "transf-duplicado-origem")
    escola_b = await criar_escola_e_gestor(client, "transf-duplicado-destino")
    headers_a = auth_headers(escola_a["token"])
    aluno_id, _ = await _matricular_aluno_ativo(client, headers_a, "Aluno Duplicado")

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Primeiro pedido"
    })
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Segundo pedido, ainda pendente o primeiro"
    })
    assert resp.status_code == 400, resp.text


async def test_pedido_de_transferencia_duplicado_e_rejeitado_reingresso(client):
    """Reingresso (CICLO_CONCLUIDO): a matrícula nunca é suspensa (não
    há "ativo" para suspender — ver criar_solicitacao), por isso é
    mesmo o check explícito de "já existe um pedido pendente" que
    bloqueia o segundo pedido."""
    escola_a = await criar_escola_e_gestor(client, "transf-duplicado-reingresso-origem")
    escola_b = await criar_escola_e_gestor(client, "transf-duplicado-reingresso-destino")
    headers_a = auth_headers(escola_a["token"])
    aluno_id, matricula_id = await _matricular_aluno_ativo(client, headers_a, "Aluno Duplicado Reingresso")
    resp = await client.patch(f"/api/v1/matriculas/{matricula_id}/status", headers=headers_a, json={
        "status_matricula": "CICLO_CONCLUIDO", "motivo": "CONCLUSAO_ESCOLARIDADE"
    })
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Primeiro pedido"
    })
    assert resp.status_code == 200, resp.text

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_b["nif"], "motivo": "Segundo pedido, ainda pendente o primeiro"
    })
    assert resp.status_code == 400, resp.text
    assert "já existe um pedido" in resp.json()["detail"].lower()


async def test_transferencia_com_nif_destino_inexistente(client):
    escola_a = await criar_escola_e_gestor(client, "transf-nif-inexistente")
    headers_a = auth_headers(escola_a["token"])
    aluno_id, _ = await _matricular_aluno_ativo(client, headers_a, "Aluno Nif Inexistente")

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": "999999999", "motivo": "teste"
    })
    assert resp.status_code == 404, resp.text


async def test_transferencia_com_nif_destino_igual_a_origem(client):
    escola_a = await criar_escola_e_gestor(client, "transf-nif-propria-escola")
    headers_a = auth_headers(escola_a["token"])
    aluno_id, _ = await _matricular_aluno_ativo(client, headers_a, "Aluno Mesma Escola")

    resp = await client.post("/api/v1/transferencias", headers=headers_a, json={
        "aluno_id": aluno_id, "nif_destino": escola_a["nif"], "motivo": "teste"
    })
    assert resp.status_code == 400, resp.text
    assert "não pode ser a mesma" in resp.json()["detail"].lower()
