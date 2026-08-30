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
