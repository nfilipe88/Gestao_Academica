"""Documentos do Aluno (AlunoDocumento) — ver app/cruds/alunos.py.
Não havia nenhum teste próprio deste ficheiro. A geração automática do
Histórico Escolar na Transferência/Reingresso (o principal uso deste
mecanismo) é testada em test_transferencias.py; aqui cobre-se o CRUD
genérico de documentos em si (upload/listar/ver/remover/isolamento)."""
import io

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


async def _criar_aluno(client, headers, nome: str = "Aluno de Teste") -> str:
    resp = await client.post(
        "/api/v1/alunos",
        json={"matricula_interna": f"AL{sufixo_unico()}", "nome_completo": nome, "data_nascimento": "2012-05-10"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_documento_aluno_upload_listar_ver_remover(client):
    escola = await criar_escola_e_gestor(client, "aluno-doc")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/documentos", headers=headers, params={"descricao": "Boletim da escola anterior"},
        files={"ficheiro": ("boletim.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    documentos = resp.json()["documentos"]
    assert len(documentos) == 1
    assert documentos[0]["descricao"] == "Boletim da escola anterior"
    doc_id = documentos[0]["id"]

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/documentos", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/alunos/{aluno_id}/documentos/{doc_id}/url", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:image/png;base64,")

    resp = await client.delete(f"/api/v1/alunos/{aluno_id}/documentos/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["documentos"] == []


async def test_documento_aluno_rejeita_tipo_invalido(client):
    escola = await criar_escola_e_gestor(client, "aluno-doc-invalido")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/documentos", headers=headers,
        files={"ficheiro": ("nota.txt", io.BytesIO(b"nao e um documento"), "text/plain")}
    )
    assert resp.status_code == 400


async def test_documento_aluno_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "aluno-doc-iso-a")
    escola_b = await criar_escola_e_gestor(client, "aluno-doc-iso-b")
    headers_a = auth_headers(escola_a["token"])
    aluno_id = await _criar_aluno(client, headers_a)

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/documentos", headers=auth_headers(escola_b["token"]),
        files={"ficheiro": ("x.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 404


async def test_listagem_de_alunos_inclui_num_responsaveis(client):
    """Regressão: GET /alunos devolvia o Aluno "nu" (sem nenhuma
    contagem de responsáveis), e o ecrã de Alunos usava só o cache
    client-side de vínculos já carregados (vazio até se expandir "Ver"
    uma vez) para o número no botão — mostrando "(0)" para todo e
    qualquer aluno na primeira vista, mesmo já tendo responsável
    vinculado. num_responsaveis calculado no back-end corrige isto."""
    escola = await criar_escola_e_gestor(client, "aluno-num-responsaveis")
    headers = auth_headers(escola["token"])
    aluno_id = await _criar_aluno(client, headers)

    resp = await client.get("/api/v1/alunos?page=1&page_size=25", headers=headers)
    assert resp.status_code == 200, resp.text
    item = next(a for a in resp.json()["items"] if a["id"] == aluno_id)
    assert item["num_responsaveis"] == 0

    resp = await client.post("/api/v1/responsaveis", headers=headers, json={
        "nome_completo": "Responsável Teste", "telefone_contato": "+244900000000"
    })
    responsavel_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/alunos/{aluno_id}/responsaveis", headers=headers, json={
        "responsavel_id": responsavel_id, "tipo_parentesco": "Mãe", "responsavel_financeiro": True
    })
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/alunos?page=1&page_size=25", headers=headers)
    item = next(a for a in resp.json()["items"] if a["id"] == aluno_id)
    assert item["num_responsaveis"] == 1
