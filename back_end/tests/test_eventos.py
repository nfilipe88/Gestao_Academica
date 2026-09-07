"""Área de Eventos da escola — ver app/cruds/eventos.py. Distinto da
galeria genérica de Site Público (test_site_publico.py): aqui cada
evento tem título/data/descrição e várias fotos, sem o limite de 8."""
import io

from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_comportamento import _criar_professor_com_token

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
    "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
    "ae426082"
)


async def _criar_evento(client, headers, *, publicado: bool = True) -> str:
    resp = await client.post("/api/v1/eventos", headers=headers, json={
        "titulo": "Feira de Ciências", "data": "2026-11-15",
        "descricao": "Projetos dos alunos do 9º ano.", "publicado": publicado,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_gestor_cria_e_lista_evento(client):
    escola = await criar_escola_e_gestor(client, "eventos-criar")
    headers = auth_headers(escola["token"])
    evento_id = await _criar_evento(client, headers)

    resp = await client.get("/api/v1/eventos", headers=headers)
    assert resp.status_code == 200, resp.text
    eventos = resp.json()
    assert len(eventos) == 1
    assert eventos[0]["id"] == evento_id
    assert eventos[0]["titulo"] == "Feira de Ciências"
    assert eventos[0]["fotos"] == []


async def test_secretaria_e_professor_nao_podem_criar_evento(client):
    escola = await criar_escola_e_gestor(client, "eventos-rbac")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Eventos")

    resp = await client.post("/api/v1/eventos", headers=auth_headers(token_professor), json={
        "titulo": "Não devia criar", "data": "2026-11-15",
    })
    assert resp.status_code == 403, resp.text


async def test_evento_aceita_mais_de_oito_fotos(client):
    """O ponto central desta funcionalidade: ao contrário da galeria de
    Site Público (limite de 8), um evento não tem limite nenhum."""
    escola = await criar_escola_e_gestor(client, "eventos-sem-limite")
    headers = auth_headers(escola["token"])
    evento_id = await _criar_evento(client, headers)

    for i in range(9):
        resp = await client.post(
            f"/api/v1/eventos/{evento_id}/fotos", headers=headers,
            files={"ficheiro": (f"foto{i}.png", io.BytesIO(_PNG_1X1), "image/png")}
        )
        assert resp.status_code == 201, resp.text

    assert len(resp.json()["fotos"]) == 9


async def test_foto_evento_rejeita_tipo_invalido(client):
    escola = await criar_escola_e_gestor(client, "eventos-foto-invalida")
    headers = auth_headers(escola["token"])
    evento_id = await _criar_evento(client, headers)

    resp = await client.post(
        f"/api/v1/eventos/{evento_id}/fotos", headers=headers,
        files={"ficheiro": ("nota.txt", io.BytesIO(b"nao e uma imagem"), "text/plain")}
    )
    assert resp.status_code == 400, resp.text


async def test_evento_nao_publicado_fica_fora_do_endpoint_publico(client):
    escola = await criar_escola_e_gestor(client, "eventos-nao-publicado")
    headers = auth_headers(escola["token"])
    await _criar_evento(client, headers, publicado=False)
    evento_publicado_id = await _criar_evento(client, headers, publicado=True)

    resp = await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={"ativo": True})
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")
    assert resp.status_code == 200, resp.text
    eventos_publicos = resp.json()["eventos"]
    assert len(eventos_publicos) == 1
    assert eventos_publicos[0]["id"] == evento_publicado_id

    # Mas continua visível para o Gestor.
    resp = await client.get("/api/v1/eventos", headers=headers)
    assert len(resp.json()) == 2


async def test_remover_evento_remove_tambem_as_fotos(client):
    escola = await criar_escola_e_gestor(client, "eventos-remover")
    headers = auth_headers(escola["token"])
    evento_id = await _criar_evento(client, headers)
    await client.post(
        f"/api/v1/eventos/{evento_id}/fotos", headers=headers,
        files={"ficheiro": ("foto.png", io.BytesIO(_PNG_1X1), "image/png")}
    )

    resp = await client.delete(f"/api/v1/eventos/{evento_id}", headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/v1/eventos", headers=headers)
    assert resp.json() == []

    resp = await client.patch(f"/api/v1/eventos/{evento_id}", headers=headers, json={"titulo": "X"})
    assert resp.status_code == 404, resp.text


async def test_eventos_isolados_por_tenant(client):
    escola_a = await criar_escola_e_gestor(client, "eventos-iso-a")
    escola_b = await criar_escola_e_gestor(client, "eventos-iso-b")
    headers_a = auth_headers(escola_a["token"])
    headers_b = auth_headers(escola_b["token"])
    evento_id = await _criar_evento(client, headers_a)

    resp = await client.get("/api/v1/eventos", headers=headers_b)
    assert resp.json() == []

    resp = await client.patch(f"/api/v1/eventos/{evento_id}", headers=headers_b, json={"titulo": "X"})
    assert resp.status_code == 404, resp.text

    resp = await client.delete(f"/api/v1/eventos/{evento_id}", headers=headers_b)
    assert resp.status_code == 404, resp.text
