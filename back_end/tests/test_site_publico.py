"""Página pública de apresentação de uma escola (marketing/angariação
de alunos) — ver app/cruds/site_publico.py."""
import io

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def test_site_publico_404_quando_desativado_por_omissao(client):
    escola = await criar_escola_e_gestor(client, "site-pub-off")
    resp = await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")
    assert resp.status_code == 404


async def test_site_publico_404_para_tenant_inexistente(client):
    import uuid
    resp = await client.get(f"/api/v1/public/escola/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_gestor_ativa_e_edita_site_publico(client):
    escola = await criar_escola_e_gestor(client, "site-pub-editar")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={
        "ativo": True, "missao": "Formar cidadãos íntegros.", "metodologia": "Aprendizagem baseada em projetos."
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["ativo"] is True

    resp = await client.get("/api/v1/configuracoes/site-publico", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["missao"] == "Formar cidadãos íntegros."


async def test_site_publico_mostra_cursos_reais_e_dados_da_escola(client):
    escola = await criar_escola_e_gestor(client, "site-pub-cursos")
    headers = auth_headers(escola["token"])

    await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={
        "ativo": True, "missao": "Missão de teste", "metodologia": None
    })
    resp = await client.post("/api/v1/academico/cursos", headers=headers, json={"nome": "Ensino Secundário"})
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["missao"] == "Missão de teste"
    assert "Ensino Secundário" in corpo["cursos"]
    assert corpo["nome_fantasia"]
    # Nunca deve vazar dados internos de gestão.
    assert "nif" not in corpo
    assert "iban" not in corpo


async def test_site_publico_desativado_de_novo_volta_a_dar_404(client):
    escola = await criar_escola_e_gestor(client, "site-pub-toggle")
    headers = auth_headers(escola["token"])
    await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={"ativo": True, "missao": None, "metodologia": None})
    assert (await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")).status_code == 200

    await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={"ativo": False, "missao": None, "metodologia": None})
    assert (await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")).status_code == 404


async def test_gestor_adiciona_e_remove_foto(client):
    escola = await criar_escola_e_gestor(client, "site-pub-foto")
    headers = auth_headers(escola["token"])

    # PNG 1x1 mínimo válido — só para passar a validação de content-type/tamanho.
    png_1x1 = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c"
        "020000000b4944415478da6364f80f00010501012718e3660000000049454e44"
        "ae426082"
    )
    resp = await client.post(
        "/api/v1/configuracoes/site-publico/fotos", headers=headers,
        files={"ficheiro": ("foto.png", io.BytesIO(png_1x1), "image/png")}
    )
    assert resp.status_code == 201, resp.text
    fotos = resp.json()["fotos"]
    assert len(fotos) == 1
    assert fotos[0]["url"].startswith("data:image/png;base64,")

    foto_id = fotos[0]["id"]
    resp = await client.delete(f"/api/v1/configuracoes/site-publico/fotos/{foto_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["fotos"] == []


async def test_foto_rejeita_tipo_invalido(client):
    escola = await criar_escola_e_gestor(client, "site-pub-foto-invalida")
    headers = auth_headers(escola["token"])
    resp = await client.post(
        "/api/v1/configuracoes/site-publico/fotos", headers=headers,
        files={"ficheiro": ("nota.txt", io.BytesIO(b"nao e uma imagem"), "text/plain")}
    )
    assert resp.status_code == 400


async def test_gestor_define_slug_e_pagina_fica_acessivel_por_ele(client):
    escola = await criar_escola_e_gestor(client, "site-pub-slug")
    headers = auth_headers(escola["token"])
    # Sufixo único (não um literal fixo tipo "colegio-do-futuro"): a BD
    # de testes não é reposta entre execuções, um slug fixo colidiria
    # consigo mesmo numa segunda corrida da suite.
    slug = f"colegio-{sufixo_unico()}"

    resp = await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={
        "ativo": True, "slug": slug.upper(), "missao": None, "metodologia": None
    })
    assert resp.status_code == 200, resp.text
    # Normalizado para minúsculas ao guardar.
    assert resp.json()["slug"] == slug

    # A página pública responde tanto pelo slug como pelo uuid original.
    resp = await client.get(f"/api/v1/public/escola/{slug}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["tenant_id"] == escola["tenant_id"]

    resp = await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")
    assert resp.status_code == 200, resp.text


async def test_slug_invalido_e_rejeitado(client):
    escola = await criar_escola_e_gestor(client, "site-pub-slug-invalido")
    headers = auth_headers(escola["token"])
    for slug_invalido in ["ab", "Tem Espaço", "maiúsculo-com-acento", "-comeca-com-hifen", "termina-com-hifen-"]:
        resp = await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={
            "ativo": True, "slug": slug_invalido, "missao": None, "metodologia": None
        })
        assert resp.status_code == 400, f"{slug_invalido!r} devia ter sido rejeitado"


async def test_slug_duplicado_entre_escolas_e_rejeitado(client):
    escola_a = await criar_escola_e_gestor(client, "site-pub-slug-dup-a")
    escola_b = await criar_escola_e_gestor(client, "site-pub-slug-dup-b")
    slug = f"mesmo-endereco-{sufixo_unico()}"
    resp = await client.put("/api/v1/configuracoes/site-publico", headers=auth_headers(escola_a["token"]), json={
        "ativo": True, "slug": slug, "missao": None, "metodologia": None
    })
    assert resp.status_code == 200, resp.text
    resp = await client.put("/api/v1/configuracoes/site-publico", headers=auth_headers(escola_b["token"]), json={
        "ativo": True, "slug": slug, "missao": None, "metodologia": None
    })
    assert resp.status_code == 400


async def test_redes_sociais_aparecem_na_pagina_publica(client):
    escola = await criar_escola_e_gestor(client, "site-pub-redes")
    headers = auth_headers(escola["token"])
    resp = await client.put("/api/v1/configuracoes/site-publico", headers=headers, json={
        "ativo": True, "missao": None, "metodologia": None,
        "facebook": "https://facebook.com/colegiodofuturo",
        "instagram": "https://instagram.com/colegiodofuturo",
        "whatsapp": "+351 912 345 678",
    })
    assert resp.status_code == 200, resp.text
    # Só dígitos guardados — o "+" e os espaços não fazem parte do número em si.
    assert resp.json()["whatsapp"] == "351912345678"

    resp = await client.get(f"/api/v1/public/escola/{escola['tenant_id']}")
    assert resp.json()["facebook"] == "https://facebook.com/colegiodofuturo"
    assert resp.json()["whatsapp"] == "351912345678"


async def test_outra_escola_nao_edita_site_publico_de_ninguem(client):
    escola_a = await criar_escola_e_gestor(client, "site-pub-iso-a")
    escola_b = await criar_escola_e_gestor(client, "site-pub-iso-b")
    await client.put("/api/v1/configuracoes/site-publico", headers=auth_headers(escola_a["token"]), json={
        "ativo": True, "missao": "Só da escola A", "metodologia": None
    })
    resp = await client.get("/api/v1/configuracoes/site-publico", headers=auth_headers(escola_b["token"]))
    assert resp.json()["missao"] is None
