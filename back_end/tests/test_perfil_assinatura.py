"""Assinatura pessoal do utilizador (AssinaturaUsuario) — self-service,
usada em documentos PDF emitidos pelo próprio quando é staff (ver
app/core/assinaturas.py). Mesmo padrão versionado de FotoPerfilAluno
(nunca apaga a anterior, arquiva-a — ver tests/test_foto_perfil.py).

Deliberadamente sem restrição de perfil no backend (ver app/api/v1/
perfil.py e app/cruds/perfil.py): um ALUNO/RESPONSAVEL também pode
enviar uma, é inofensivo — nunca é lida em nenhum PDF (só GESTOR/
SECRETARIA/PROFESSOR contam para app/core/assinaturas.py); o filtro
real é visual, no frontend."""
import io

from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_comportamento import _criar_professor_com_token

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


async def test_assinatura_pessoal_upload_e_leitura(client):
    escola = await criar_escola_e_gestor(client, "assinatura-pessoal-crud")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/perfil", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["tem_assinatura_pessoal"] is False

    resp = await client.post(
        "/api/v1/perfil/assinatura", headers=headers,
        files={"ficheiro": ("assinatura.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["tem_assinatura_pessoal"] is True

    resp = await client.get("/api/v1/perfil/assinatura", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["url"].startswith("data:image/png;base64,")


async def test_assinatura_pessoal_substituicao_arquiva_a_anterior_mas_continua_so_uma_ativa(client):
    escola = await criar_escola_e_gestor(client, "assinatura-pessoal-substituir")
    headers = auth_headers(escola["token"])

    await client.post(
        "/api/v1/perfil/assinatura", headers=headers,
        files={"ficheiro": ("a.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    resp = await client.post(
        "/api/v1/perfil/assinatura", headers=headers,
        files={"ficheiro": ("b.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["tem_assinatura_pessoal"] is True


async def test_assinatura_pessoal_remover(client):
    escola = await criar_escola_e_gestor(client, "assinatura-pessoal-remover")
    headers = auth_headers(escola["token"])
    await client.post(
        "/api/v1/perfil/assinatura", headers=headers,
        files={"ficheiro": ("a.png", io.BytesIO(_PNG_1X1), "image/png")}
    )

    resp = await client.delete("/api/v1/perfil/assinatura", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["tem_assinatura_pessoal"] is False

    resp = await client.get("/api/v1/perfil/assinatura", headers=headers)
    assert resp.status_code == 404


async def test_assinatura_pessoal_rejeita_tipo_invalido(client):
    escola = await criar_escola_e_gestor(client, "assinatura-pessoal-invalida")
    headers = auth_headers(escola["token"])
    resp = await client.post(
        "/api/v1/perfil/assinatura", headers=headers,
        files={"ficheiro": ("doc.pdf", io.BytesIO(b"%PDF-1.4 nao e assinatura"), "application/pdf")}
    )
    assert resp.status_code == 400


async def test_assinatura_pessoal_isolada_por_utilizador(client):
    """Um Professor e um Gestor da mesma escola têm assinaturas
    independentes — cada um só vê/gere a própria conta (ver docstring de
    app/cruds/perfil.py: nunca recebe um usuario_id de fora)."""
    escola = await criar_escola_e_gestor(client, "assinatura-pessoal-iso")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Assinatura")
    headers_professor = auth_headers(token_professor)

    resp = await client.post(
        "/api/v1/perfil/assinatura", headers=headers,
        files={"ficheiro": ("gestor.png", io.BytesIO(_PNG_1X1), "image/png")}
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/perfil", headers=headers_professor)
    assert resp.status_code == 200, resp.text
    assert resp.json()["tem_assinatura_pessoal"] is False

    resp = await client.get("/api/v1/perfil/assinatura", headers=headers_professor)
    assert resp.status_code == 404
