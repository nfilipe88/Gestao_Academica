"""Relatório (PDF) e Exportação (CSV) do Painel de Indicadores — ver
app/cruds/indicadores.py. Não havia nenhum teste do módulo Indicadores
antes desta sessão; cobertura aqui focada no que foi acrescentado
("relatórios/exportação de indicadores"), não uma reescrita completa
do módulo (obter_indicadores/obter_risco_evasao já são só agregação,
sem regra de negócio própria a testar aqui)."""
import io

from pypdf import PdfReader

from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_comportamento import _criar_professor_com_token
from tests.test_portal_alertas_propina import _preparar_aluno_com_fatura_em_atraso


def _texto_pdf(conteudo: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(conteudo)).pages)


async def test_relatorio_pdf_inclui_todas_as_seccoes(client):
    escola = await criar_escola_e_gestor(client, "indicadores-relatorio")
    headers = auth_headers(escola["token"])
    await _preparar_aluno_com_fatura_em_atraso(client, headers)

    resp = await client.get("/api/v1/indicadores/relatorio.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")

    texto = _texto_pdf(resp.content)
    assert "Relatório de Indicadores" in texto
    assert "Ocupação por turma" in texto
    assert "Desempenho médio por turma" in texto
    assert "Financeiro" in texto
    assert "Funil do CRM" in texto
    assert "Eficiência por Objetivo de Aprendizagem" in texto
    assert "Risco de Evasão" in texto
    # O aluno com a mensalidade atrasada aparece na secção de risco.
    assert "Aluno Portal" in texto
    assert "Turma A" in texto


async def test_relatorio_pdf_bloqueado_para_professor(client):
    escola = await criar_escola_e_gestor(client, "indicadores-relatorio-rbac")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Indicadores")

    resp = await client.get("/api/v1/indicadores/relatorio.pdf", headers=auth_headers(token_professor))
    assert resp.status_code == 403, resp.text


async def test_exportar_risco_evasao_csv(client):
    escola = await criar_escola_e_gestor(client, "indicadores-csv")
    headers = auth_headers(escola["token"])
    await _preparar_aluno_com_fatura_em_atraso(client, headers)

    resp = await client.get("/api/v1/indicadores/risco-evasao/exportar.csv", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in resp.headers["content-disposition"]
    assert "risco-evasao.csv" in resp.headers["content-disposition"]

    # utf-8-sig porque o CSV sai com BOM (para o Excel abrir acentos
    # sem o utilizador ter de escolher a codificação manualmente).
    texto = resp.content.decode("utf-8-sig")
    linhas = texto.strip().splitlines()
    assert linhas[0].startswith("Aluno,Turma,Nível de risco")
    assert any("Aluno Portal" in linha and "Turma A" in linha and "mensalidade vencida" in linha for linha in linhas[1:])


async def test_exportar_risco_evasao_csv_vazio_nao_rebenta(client):
    """Uma escola sem nenhum sinal de risco ainda tem de devolver um
    CSV válido — só com o cabeçalho, não um erro."""
    escola = await criar_escola_e_gestor(client, "indicadores-csv-vazio")
    headers = auth_headers(escola["token"])

    resp = await client.get("/api/v1/indicadores/risco-evasao/exportar.csv", headers=headers)
    assert resp.status_code == 200, resp.text
    texto = resp.content.decode("utf-8-sig")
    linhas = texto.strip().splitlines()
    assert len(linhas) == 1
    assert linhas[0].startswith("Aluno,Turma,Nível de risco")


async def test_exportar_risco_evasao_csv_bloqueado_para_professor(client):
    escola = await criar_escola_e_gestor(client, "indicadores-csv-rbac")
    headers = auth_headers(escola["token"])
    _, token_professor = await _criar_professor_com_token(client, headers, "Prof. Indicadores CSV")

    resp = await client.get("/api/v1/indicadores/risco-evasao/exportar.csv", headers=auth_headers(token_professor))
    assert resp.status_code == 403, resp.text
