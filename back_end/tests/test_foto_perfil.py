"""Foto de Perfil do Aluno (FotoPerfilAluno) — ver app/cruds/alunos.py.
A foto que vale para o cartão de acesso. Deve ser renovada todos os
anos, mas isso não é imposto como bloqueio: enviar uma nova nunca
apaga a anterior, só a arquiva (ativa=False) — é assim que se
acompanha a evolução do aluno ao longo dos anos. Cobre o upload/
listar/ver por parte da Secretaria (ecrã de Alunos) e o self-service
pelo Portal (aluno/responsável, com verificação de posse)."""
import io

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_rematricula import _criar_aluno_matriculado_com_portal

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


async def _criar_aluno(client, headers, nome: str = "Aluno Foto") -> str:
    resp = await client.post(
        "/api/v1/alunos",
        json={"matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-05-10"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_foto_perfil_upload_arquiva_a_anterior(client):
    escola = await criar_escola_e_gestor(client, "foto-perfil-crud")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/foto-perfil", headers=headers,
        files={"ficheiro": ("2026.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    fotos = resp.json()["fotos"]
    assert len(fotos) == 1
    assert fotos[0]["ativa"] is True
    assert fotos[0]["ano_letivo"] >= 2026

    # Uma segunda foto (renovação anual) arquiva a primeira — nunca a apaga.
    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/foto-perfil", headers=headers,
        files={"ficheiro": ("2027.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    fotos = resp.json()["fotos"]
    assert len(fotos) == 2, "a foto antiga deve continuar no histórico, arquivada"
    ativas = [f for f in fotos if f["ativa"]]
    assert len(ativas) == 1, "só pode haver uma foto ativa (a do cartão de acesso) de cada vez"
    assert ativas[0]["nome_original"] == "2027.png"

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/fotos-perfil", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2

    foto_ativa_id = ativas[0]["id"]
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/fotos-perfil/{foto_ativa_id}/url", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:image/png;base64,")


async def test_foto_perfil_rejeita_tipo_invalido(client):
    """Ao contrário dos documentos de apoio (AlunoDocumento), PDF não é
    aceite aqui — não faz sentido para uma foto tipo cartão."""
    escola = await criar_escola_e_gestor(client, "foto-perfil-invalida")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/foto-perfil", headers=headers,
        files={"ficheiro": ("doc.pdf", io.BytesIO(b"%PDF-1.4 nao e uma foto"), "application/pdf")}
    )
    assert resp.status_code == 400


async def test_foto_perfil_isolada_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "foto-perfil-iso-a")
    escola_b = await criar_escola_e_gestor(client, "foto-perfil-iso-b")
    headers_a = auth_headers(escola_a["token"])
    aluno_id = await _criar_aluno(client, headers_a)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/foto-perfil", headers=auth_headers(escola_b["token"]),
        files={"ficheiro": ("x.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 404


async def test_foto_perfil_professor_so_pode_ler(client):
    """_PODE_GERIR (upload) é GESTOR/SECRETARIA; leitura fica aberta a
    qualquer funcionário (exigir_perfil_staff) — mesmo alcance dos
    documentos de apoio."""
    escola = await criar_escola_e_gestor(client, "foto-perfil-professor")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Foto")
    headers_professor = auth_headers(token_professor)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/foto-perfil", headers=headers_professor,
        files={"ficheiro": ("x.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 403, resp.text

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/fotos-perfil", headers=headers_professor)
    assert resp.status_code == 200, resp.text


async def test_portal_foto_perfil_self_service(client):
    """O próprio aluno ou o encarregado envia a foto pelo Portal."""
    from datetime import date
    escola = await criar_escola_e_gestor(client, "portal-foto-self")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    token_responsavel = resp.json()["access_token"]

    resp = await client.post(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/foto-perfil", headers=auth_headers(token_responsavel),
        files={"ficheiro": ("filho.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    fotos = resp.json()["fotos"]
    assert len(fotos) == 1
    assert fotos[0]["ativa"] is True

    resp = await client.get(f"/api/v1/portal/educandos/{dados['aluno_id']}/fotos-perfil", headers=auth_headers(token_responsavel))
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1

    foto_id = fotos[0]["id"]
    resp = await client.get(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/fotos-perfil/{foto_id}/url", headers=auth_headers(token_responsavel)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:image/png;base64,")

    # E já aparece do lado da Secretaria também — é o mesmo registo.
    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/fotos-perfil", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1


async def test_cartao_acesso_pdf_com_foto_e_turma(client):
    """O cartão de acesso (formato cartão, ver app/core/documentos_pdf.py
    ::gerar_pdf_cartao_acesso) é gerado no momento, pronto a imprimir —
    não é um documento pedido/pago (Solicitações de Documentos)."""
    from datetime import date
    escola = await criar_escola_e_gestor(client, "cartao-acesso-completo")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)

    resp = await client.post(
        f"/api/v1/alunos/{dados['aluno_id']}/foto-perfil", headers=headers,
        files={"ficheiro": ("cartao.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/alunos/{dados['aluno_id']}/cartao-acesso.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


async def test_cartao_acesso_pdf_sem_foto_nao_bloqueia(client):
    """Um aluno sem fotografia nenhuma ainda deve poder ter o cartão
    emitido (com um espaço reservado no lugar da foto) — a Secretaria
    não devia ficar bloqueada por isso."""
    escola = await criar_escola_e_gestor(client, "cartao-acesso-sem-foto")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/cartao-acesso.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.content.startswith(b"%PDF")


async def test_cartao_acesso_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "cartao-acesso-iso-a")
    escola_b = await criar_escola_e_gestor(client, "cartao-acesso-iso-b")
    headers_a = auth_headers(escola_a["token"])
    aluno_id = await _criar_aluno(client, headers_a)

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/cartao-acesso.pdf", headers=auth_headers(escola_b["token"]))
    assert resp.status_code == 404


async def test_portal_cartao_acesso_self_service(client):
    from datetime import date
    escola = await criar_escola_e_gestor(client, "portal-cartao-self")
    headers = auth_headers(escola["token"])
    dados = await _criar_aluno_matriculado_com_portal(client, headers, date.today().year)

    resp = await client.post("/api/v1/auth/login", data={"username": dados["email_responsavel"], "password": dados["senha"]})
    token_responsavel = resp.json()["access_token"]

    resp = await client.get(
        f"/api/v1/portal/educandos/{dados['aluno_id']}/cartao-acesso.pdf", headers=auth_headers(token_responsavel)
    )
    assert resp.status_code == 200, resp.text
    assert resp.content.startswith(b"%PDF")


async def test_portal_cartao_acesso_bloqueia_outra_familia(client):
    from datetime import date
    escola = await criar_escola_e_gestor(client, "portal-cartao-posse")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    familia_a = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    familia_b = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.post("/api/v1/auth/login", data={"username": familia_a["email_responsavel"], "password": familia_a["senha"]})
    token_responsavel_a = resp.json()["access_token"]

    resp = await client.get(
        f"/api/v1/portal/educandos/{familia_b['aluno_id']}/cartao-acesso.pdf", headers=auth_headers(token_responsavel_a)
    )
    assert resp.status_code == 403, resp.text


async def test_portal_foto_perfil_bloqueia_outra_familia(client):
    """Posse (garantir_aluno_permitido) — duas famílias na MESMA escola,
    um responsável não pode enviar/ver a foto do educando de outra."""
    from datetime import date
    escola = await criar_escola_e_gestor(client, "portal-foto-posse")
    headers = auth_headers(escola["token"])
    ano_letivo = date.today().year
    familia_a = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)
    familia_b = await _criar_aluno_matriculado_com_portal(client, headers, ano_letivo)

    resp = await client.post("/api/v1/auth/login", data={"username": familia_a["email_responsavel"], "password": familia_a["senha"]})
    token_responsavel_a = resp.json()["access_token"]
    headers_resp_a = auth_headers(token_responsavel_a)

    resp = await client.post(
        f"/api/v1/portal/educandos/{familia_b['aluno_id']}/foto-perfil", headers=headers_resp_a,
        files={"ficheiro": ("x.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 403, resp.text

    resp = await client.get(f"/api/v1/portal/educandos/{familia_b['aluno_id']}/fotos-perfil", headers=headers_resp_a)
    assert resp.status_code == 403, resp.text
