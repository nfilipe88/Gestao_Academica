"""Cartões de acesso em lote, por turma — ver
app/cruds/alunos.py::gerar_cartoes_acesso_turma e
app/core/documentos_pdf.py::gerar_pdf_cartoes_acesso_lote.

Caso de uso real (Angola): a Secretaria imprime de uma vez os cartões
de uma turma inteira ao início do ano letivo, em vez de aluno a aluno
pelo ecrã de Alunos (que já existia — ver test_foto_perfil.py)."""
import io

from pypdf import PdfReader

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico
from tests.test_comportamento import _criar_professor_com_token
from tests.test_matricula_financeiro import _preparar_turma_com_vaga
from tests.test_foto_perfil import _PNG_1X1

_ANO_LETIVO = 2026


def _texto_paginas(conteudo: bytes) -> list[str]:
    return [pagina.extract_text() for pagina in PdfReader(io.BytesIO(conteudo)).pages]


async def _matricular_aluno(client, headers, turma_id: str, nome: str) -> tuple[str, str]:
    """Cria um aluno e matricula-o ATIVO na turma dada. Devolve
    (aluno_id, matricula_id)."""
    suf = sufixo_unico()
    resp = await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{suf}", "nome_completo": nome, "data_nascimento": "2012-05-10"
    })
    assert resp.status_code == 201, resp.text
    aluno_id = resp.json()["id"]

    resp = await client.post("/api/v1/matriculas", headers=headers,
                              json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": _ANO_LETIVO})
    assert resp.status_code == 201, resp.text
    return aluno_id, resp.json()["id"]


async def test_cartoes_acesso_lote_um_por_pagina_ordem_alfabetica(client):
    escola = await criar_escola_e_gestor(client, "cartoes-lote-completo")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, _ANO_LETIVO)

    # De propósito fora de ordem alfabética na criação, para confirmar
    # que a listagem no PDF vem ordenada por nome_completo.
    zeca_id, _ = await _matricular_aluno(client, headers, turma_id, "Zeca Terceiro")
    ana_id, _ = await _matricular_aluno(client, headers, turma_id, "Ana Primeira")
    bruno_id, _ = await _matricular_aluno(client, headers, turma_id, "Bruno Segundo")

    # Só a Ana tem foto — confirma que a ausência de foto não bloqueia
    # nenhum cartão do lote (mesmo comportamento do cartão individual).
    resp = await client.post(
        f"/api/v1/alunos/{ana_id}/foto-perfil", headers=headers,
        files={"ficheiro": ("ana.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/turmas/{turma_id}/cartoes-acesso.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")

    paginas = _texto_paginas(resp.content)
    assert len(paginas) == 3, "um cartão por página, um por aluno ativo na turma"
    assert "Ana Primeira" in paginas[0]
    assert "Bruno Segundo" in paginas[1]
    assert "Zeca Terceiro" in paginas[2]
    for pagina in paginas:
        assert "10º A" in pagina

    del zeca_id, bruno_id  # só usados para criar as matrículas acima


async def test_cartoes_acesso_lote_ignora_matricula_inativa(client):
    escola = await criar_escola_e_gestor(client, "cartoes-lote-inativa")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, _ANO_LETIVO)

    _, matricula_transferido_id = await _matricular_aluno(client, headers, turma_id, "Aluno Transferido")
    ativo_id, _ = await _matricular_aluno(client, headers, turma_id, "Aluno Ativo")

    resp = await client.patch(
        f"/api/v1/matriculas/{matricula_transferido_id}/status", headers=headers,
        json={"status_matricula": "TRANSFERIDO"}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/turmas/{turma_id}/cartoes-acesso.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    paginas = _texto_paginas(resp.content)
    assert len(paginas) == 1
    assert "Aluno Ativo" in paginas[0]

    del ativo_id


async def test_cartoes_acesso_lote_turma_sem_alunos_ativos(client):
    escola = await criar_escola_e_gestor(client, "cartoes-lote-vazia")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, _ANO_LETIVO)

    resp = await client.get(f"/api/v1/turmas/{turma_id}/cartoes-acesso.pdf", headers=headers)
    assert resp.status_code == 400, resp.text


async def test_cartoes_acesso_lote_turma_inexistente(client):
    escola = await criar_escola_e_gestor(client, "cartoes-lote-404")
    headers = auth_headers(escola["token"])

    resp = await client.get(
        "/api/v1/turmas/00000000-0000-0000-0000-000000000000/cartoes-acesso.pdf", headers=headers
    )
    assert resp.status_code == 404, resp.text


async def test_cartoes_acesso_lote_isolado_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "cartoes-lote-iso-a")
    escola_b = await criar_escola_e_gestor(client, "cartoes-lote-iso-b")
    headers_a = auth_headers(escola_a["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers_a, _ANO_LETIVO)
    await _matricular_aluno(client, headers_a, turma_id, "Aluno Escola A")

    resp = await client.get(
        f"/api/v1/turmas/{turma_id}/cartoes-acesso.pdf", headers=auth_headers(escola_b["token"])
    )
    assert resp.status_code == 404, resp.text


async def test_cartoes_acesso_lote_professor_pode_ler(client):
    """Mesmo RBAC do cartão individual (exigir_perfil_staff) — leitura
    aberta a qualquer funcionário, não só GESTOR/SECRETARIA."""
    escola = await criar_escola_e_gestor(client, "cartoes-lote-professor")
    headers = auth_headers(escola["token"])
    turma_id = await _preparar_turma_com_vaga(client, headers, _ANO_LETIVO)
    await _matricular_aluno(client, headers, turma_id, "Aluno Qualquer")
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Cartões")

    resp = await client.get(
        f"/api/v1/turmas/{turma_id}/cartoes-acesso.pdf", headers=auth_headers(token_professor)
    )
    assert resp.status_code == 200, resp.text
