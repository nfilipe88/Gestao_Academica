"""Todo o schema Pydantic usado como corpo de um pedido (POST/PUT/PATCH) tem
de recusar campos não declarados (`model_config = {"extra": "forbid"}`) — sem
isto, o Pydantic v2 por omissão IGNORA campos extra em silêncio: um campo a
mais no corpo (typo, tentativa de injetar algo como `perfil_acesso` ou
`ativo` que o schema não pretendia deixar mudar) passava despercebido em vez
de dar um erro claro.

Descobre os schemas de entrada automaticamente a partir das próprias rotas
(`dados: NomeDoSchema` em app/api/v1/*.py, a convenção usada em toda a API) —
tal como test_rls_isolamento.py cobre tabelas novas sozinho, este cobre
endpoints novos sozinho: ninguém precisa de se lembrar de acrescentar aqui um
schema que acabou de criar."""
import importlib
import pkgutil
import re

import app.schemas as pacote_schemas

_PARAM_RE = re.compile(r"dados:\s*([A-Z]\w*)")  # nomes de classe começam sempre por maiúscula — evita apanhar "dados: tenant=..." de um log


def _nomes_dos_schemas_de_entrada() -> set[str]:
    import pathlib
    api_dir = pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
    nomes = set()
    for ficheiro in api_dir.glob("*.py"):
        texto = ficheiro.read_text(encoding="utf-8")
        nomes.update(_PARAM_RE.findall(texto))
    return nomes


def _resolver_classe(nome: str):
    """Procura `nome` em cada submódulo de app.schemas — devolve None se não for uma classe real ali."""
    for info in pkgutil.iter_modules(pacote_schemas.__path__):
        modulo = importlib.import_module(f"app.schemas.{info.name}")
        classe = getattr(modulo, nome, None)
        if isinstance(classe, type):
            return classe
    return None


def test_todos_os_schemas_de_entrada_tem_extra_forbid():
    nomes = _nomes_dos_schemas_de_entrada()
    assert len(nomes) > 90, "a descoberta automática encontrou poucos schemas — confirmar o regex/convenção `dados: Nome`"

    sem_forbid = []
    nao_resolvidos = []
    for nome in sorted(nomes):
        classe = _resolver_classe(nome)
        if classe is None:
            nao_resolvidos.append(nome)
            continue
        if getattr(classe, "model_config", {}).get("extra") != "forbid":
            sem_forbid.append(nome)

    assert not nao_resolvidos, f"schemas referenciados numa rota mas não encontrados em app/schemas: {nao_resolvidos}"
    assert not sem_forbid, (
        f"schema(s) de entrada SEM extra=\"forbid\" — um cliente pode enviar campos não declarados sem aviso nenhum: {sem_forbid}"
    )


async def test_um_campo_nao_declarado_e_recusado_com_422_ponta_a_ponta(client):
    """Confirma que a proteção funciona mesmo pela API real, não só na
    declaração do schema — usa AlunoCreate (o mais simples de montar)."""
    from tests.conftest import auth_headers, criar_escola_e_gestor
    escola = await criar_escola_e_gestor(client, "extra-forbid-e2e")
    resp = await client.post("/api/v1/alunos", headers=auth_headers(escola["token"]), json={
        "matricula_interna": "X1", "nome_completo": "Aluno", "data_nascimento": "2012-01-01",
        "perfil_acesso": "SUPER_ADMIN",  # campo que AlunoCreate nunca declarou
    })
    assert resp.status_code == 422, resp.text
    assert any(e.get("loc", [])[-1] == "perfil_acesso" and e.get("type") == "extra_forbidden" for e in resp.json()["detail"])
