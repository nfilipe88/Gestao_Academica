"""Mapa de Permissões — tabela global (sem tenant_id), semeada por
migração (ver alembic/versions/584537bbba2e_permissao_modulo.py e
d3f1a9c6b204_permissao_modulo_comportamento.py, que acrescentou a
linha "Comportamento"). Não havia nenhum teste deste módulo antes."""
from tests.conftest import auth_headers, criar_escola_e_gestor


async def test_mapa_inclui_comportamento_com_niveis_esperados(client):
    escola = await criar_escola_e_gestor(client, "permissoes-comportamento")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/permissoes", headers=headers)
    assert resp.status_code == 200, resp.text
    linhas = {(l["modulo"], l["perfil"]): l for l in resp.json()}

    # Gestor/Secretaria: TOTAL. Professor: ler+atualizar (lançar um
    # incidente), sem criar/apagar ao nível grosseiro do mapa — o mapa
    # não representa a nuance extra de "só remove os seus próprios
    # registos" (ver cruds/comportamento.py). Aluno/Responsável: só
    # leitura (é o que aparece no Dashboard do Portal).
    gestor = linhas[("Comportamento", "gestor")]
    assert (gestor["pode_criar"], gestor["pode_ler"], gestor["pode_atualizar"], gestor["pode_apagar"]) == (True, True, True, True)

    professor = linhas[("Comportamento", "professor")]
    assert (professor["pode_criar"], professor["pode_ler"], professor["pode_atualizar"], professor["pode_apagar"]) == (False, True, True, False)

    aluno_responsavel = linhas[("Comportamento", "aluno_responsavel")]
    assert (aluno_responsavel["pode_criar"], aluno_responsavel["pode_ler"], aluno_responsavel["pode_atualizar"], aluno_responsavel["pode_apagar"]) == (False, True, False, False)

    # Fica logo a seguir a "Diário de Classe" na ordem de exibição.
    assert linhas[("Comportamento", "gestor")]["ordem"] == linhas[("Diário de Classe", "gestor")]["ordem"] + 1


async def test_secretaria_nao_acede_ao_mapa_de_permissoes(client):
    """_PODE_ACEDER em api/v1/permissoes.py é SUPER_ADMIN + GESTOR só —
    a Secretaria tem o mesmo alcance do Gestor em quase tudo (ver
    test_suporte.py), mas aqui é deliberadamente bloqueada."""
    escola = await criar_escola_e_gestor(client, "permissoes-rbac-secretaria")
    headers = auth_headers(escola["token"])
    resp = await client.post("/api/v1/usuarios/secretaria", headers=headers, json={
        "nome_completo": "Secretaria Permissoes", "email": f"sec.perm.{escola['nif']}@teste.pt", "palavra_passe": "SenhaTeste123!"
    })
    assert resp.status_code == 201, resp.text
    resp_login = await client.post("/api/v1/auth/login", data={
        "username": f"sec.perm.{escola['nif']}@teste.pt", "password": "SenhaTeste123!"
    })
    headers_secretaria = auth_headers(resp_login.json()["access_token"])

    resp = await client.get("/api/v1/permissoes", headers=headers_secretaria)
    assert resp.status_code == 403, resp.text

    resp = await client.get("/api/v1/permissoes", headers=headers)
    permissao_id = resp.json()[0]["id"]
    resp = await client.patch(f"/api/v1/permissoes/{permissao_id}", headers=headers_secretaria, json={
        "pode_criar": True, "pode_ler": True, "pode_atualizar": True, "pode_apagar": True
    })
    assert resp.status_code == 403, resp.text


async def test_atualizar_permissao_persiste_a_alteracao(client):
    """PATCH /permissoes/{id} — editar uma célula fica guardado (a UI
    edita direto, sem passo de "guardar"). É uma tabela GLOBAL (sem
    tenant_id) e os testes correm contra uma base persistente sem reset
    automático entre execuções (ver docstring de tests/conftest.py) —
    por isso este teste parte do valor que encontrar (não assume um
    default fixo) e restaura-o no fim, em vez de deixar a mutação
    contaminar outros testes deste ficheiro ou execuções futuras."""
    escola = await criar_escola_e_gestor(client, "permissoes-patch")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/permissoes", headers=headers)
    assert resp.status_code == 200, resp.text
    linha = next(l for l in resp.json() if l["modulo"] == "Comportamento" and l["perfil"] == "aluno_responsavel")
    valor_original = linha["pode_atualizar"]

    try:
        resp = await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers, json={
            "pode_criar": linha["pode_criar"], "pode_ler": linha["pode_ler"],
            "pode_atualizar": not valor_original, "pode_apagar": linha["pode_apagar"]
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["pode_atualizar"] is (not valor_original)

        resp = await client.get("/api/v1/permissoes", headers=headers)
        linha_atualizada = next(l for l in resp.json() if l["id"] == linha["id"])
        assert linha_atualizada["pode_atualizar"] is (not valor_original)
    finally:
        resp = await client.patch(f"/api/v1/permissoes/{linha['id']}", headers=headers, json={
            "pode_criar": linha["pode_criar"], "pode_ler": linha["pode_ler"],
            "pode_atualizar": valor_original, "pode_apagar": linha["pode_apagar"]
        })
        assert resp.status_code == 200, resp.text
