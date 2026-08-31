"""Layouts personalizados por escola (TemplateDocumentoPersonalizado) —
ver app/cruds/documentos.py. Não havia nenhum teste deste módulo antes;
cobertura aqui focada no que esta sessão acrescentou (Cartão de
Acesso), não uma reescrita completa dos 5 tipos de documento formais.

Cartão de Acesso é deliberadamente diferente dos outros: é
personalizável (TIPOS_DOCUMENTO_PERSONALIZAVEL), mas NÃO é um
documento que a família pede/paga (TIPOS_DOCUMENTO, sem alteração) —
por isso vários testes aqui confirmam explicitamente que continua de
fora da Tabela de Preços."""
import io

from pypdf import PdfReader

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


def _texto_pdf(conteudo: bytes) -> str:
    return PdfReader(io.BytesIO(conteudo)).pages[0].extract_text()


async def _criar_aluno_com_turma(client, headers) -> str:
    from datetime import date
    resp = await client.post("/api/v1/academico/cursos", headers=headers, json={"nome": "Curso"})
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", headers=headers, json={"curso_id": curso_id, "nome": "Série"})
    serie_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/turmas", headers=headers, json={
        "serie_ano_id": serie_id, "nome_codigo": "Turma Templates", "ano_letivo": date.today().year, "vagas_maximas": 30
    })
    turma_id = resp.json()["id"]
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": "Aluno Templates", "data_nascimento": "2012-05-10"
    })
    aluno_id = resp.json()["id"]
    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": date.today().year})
    assert resp.status_code == 201, resp.text
    return aluno_id


async def test_lista_de_templates_inclui_cartao_acesso_mas_nao_precos(client):
    escola = await criar_escola_e_gestor(client, "templates-lista")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/documentos/templates", headers=headers)
    assert resp.status_code == 200, resp.text
    tipos = {t["tipo_documento"]: t for t in resp.json()}
    assert "CARTAO_ACESSO" in tipos
    assert tipos["CARTAO_ACESSO"]["personalizado"] is False
    assert tipos["CARTAO_ACESSO"]["nome"] == "Cartão de Acesso"

    # Não é um documento que a família pede/paga — nunca aparece na
    # Tabela de Preços nem seria aceite lá.
    resp = await client.get("/api/v1/documentos/precos", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "CARTAO_ACESSO" not in {p["tipo_documento"] for p in resp.json()}

    resp = await client.put("/api/v1/documentos/precos/CARTAO_ACESSO", headers=headers, json={"preco": "10.00", "ativo": True})
    assert resp.status_code == 400, resp.text


async def test_cartao_acesso_personalizado_usado_na_emissao_real(client):
    escola = await criar_escola_e_gestor(client, "templates-cartao-custom")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno_com_turma(client, headers)

    # Antes de personalizar, o cartão usa o layout nativo.
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/cartao-acesso.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "Cartão de Acesso" in _texto_pdf(resp.content)
    assert "Colégio da Praia Grande" not in _texto_pdf(resp.content)

    corpo_personalizado = (
        '<div style="font-family: Helvetica;">'
        '<p>Colégio da Praia Grande — {{ aluno_nome }}</p>'
        '<p>Matrícula {{ matricula_interna }}</p>'
        "</div>"
    )
    resp = await client.put("/api/v1/documentos/templates/CARTAO_ACESSO", headers=headers, json={"corpo_html": corpo_personalizado})
    assert resp.status_code == 200, resp.text
    assert resp.json()["personalizado"] is True

    resp = await client.get("/api/v1/documentos/templates", headers=headers)
    tipos = {t["tipo_documento"]: t for t in resp.json()}
    assert tipos["CARTAO_ACESSO"]["personalizado"] is True

    # A emissão real do cartão passa a usar o layout da escola.
    resp = await client.get(f"/api/v1/alunos/{aluno_id}/cartao-acesso.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    texto = _texto_pdf(resp.content)
    assert "Colégio da Praia Grande" in texto
    assert "Aluno Templates" in texto

    # Repor o padrão volta ao layout nativo.
    resp = await client.delete("/api/v1/documentos/templates/CARTAO_ACESSO", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["personalizado"] is False

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/cartao-acesso.pdf", headers=headers)
    texto = _texto_pdf(resp.content)
    assert "Colégio da Praia Grande" not in texto
    assert "Cartão de Acesso" in texto


async def test_cartao_acesso_pre_visualizar_nao_toca_num_aluno_real(client):
    escola = await criar_escola_e_gestor(client, "templates-cartao-preview")
    headers = auth_headers(escola["token"])

    resp = await client.post(
        "/api/v1/documentos/templates/CARTAO_ACESSO/pre-visualizar", headers=headers,
        json={"corpo_html": "<p>Pré-visualização — {{ aluno_nome }} ({{ matricula_interna }})</p>"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    texto = _texto_pdf(resp.content)
    assert "Maria Exemplo da Silva" in texto  # dados de amostra, não um aluno real

    # Nunca foi guardado — a lista continua a mostrar o padrão.
    resp = await client.get("/api/v1/documentos/templates", headers=headers)
    tipos = {t["tipo_documento"]: t for t in resp.json()}
    assert tipos["CARTAO_ACESSO"]["personalizado"] is False


async def test_cartao_acesso_template_invalido_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "templates-cartao-invalido")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/documentos/templates/CARTAO_ACESSO", headers=headers, json={
        "corpo_html": "<p>{{ aluno_nome</p>"  # Jinja mal formado
    })
    assert resp.status_code == 400, resp.text

    resp = await client.post(
        "/api/v1/documentos/templates/CARTAO_ACESSO/pre-visualizar", headers=headers,
        json={"corpo_html": "<p>{% for %}</p>"}
    )
    assert resp.status_code == 400, resp.text


async def test_cartao_acesso_personalizacao_isolada_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "templates-cartao-iso-a")
    escola_b = await criar_escola_e_gestor(client, "templates-cartao-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    aluno_id = await _criar_aluno_com_turma(client, headers_b)

    resp = await client.put("/api/v1/documentos/templates/CARTAO_ACESSO", headers=headers_a, json={
        "corpo_html": "<p>Só a escola A tem isto — {{ aluno_nome }}</p>"
    })
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/cartao-acesso.pdf", headers=headers_b)
    assert resp.status_code == 200, resp.text
    assert "Só a escola A tem isto" not in _texto_pdf(resp.content)


async def test_apenas_gestor_gere_templates(client):
    """_PODE_GERIR_PRECOS é GESTOR só — a Secretaria (mesmo alcance do
    Gestor em quase tudo) fica de fora aqui."""
    escola = await criar_escola_e_gestor(client, "templates-rbac")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Templates")

    resp = await client.get("/api/v1/documentos/templates", headers=auth_headers(token_professor))
    assert resp.status_code == 403, resp.text

    resp = await client.put("/api/v1/documentos/templates/CARTAO_ACESSO", headers=auth_headers(token_professor), json={
        "corpo_html": "<p>x</p>"
    })
    assert resp.status_code == 403, resp.text
