"""Bloco de assinaturas do envelope comum de PDF (app/core/documentos_pdf.py
::_ENVELOPE) — teste unitário puro (sem BD, sem HTTP): inspeciona o HTML
gerado diretamente, porque o PDF final é binário (xhtml2pdf comprime os
streams) e não dá para procurar texto/imagem nos bytes finais. Ver
app/core/assinaturas.py::obter_assinantes_documento para quem decide a
lista `assinantes` antes de chegar aqui."""
from app.core import documentos_pdf


def _bloco_assinaturas(html: str) -> str:
    # Tabela (não flex/div) de propósito — xhtml2pdf não suporta CSS
    # flexbox (bug real apanhado ao verificar visualmente um PDF gerado:
    # com `display: flex` os assinantes saíam empilhados verticalmente,
    # não lado a lado); tabela é o mesmo padrão já usado em table.notas.
    return html.split('<table class="assinaturas">')[1].split('</table>')[0]


def _renderizar(assinantes=None) -> str:
    return documentos_pdf._ENVELOPE.render(
        escola_nome="Colégio de Teste", escola_razao_social="", escola_nif="",
        escola_morada="", escola_contacto="", escola_logo_data_uri=None,
        assinantes=assinantes or [],
        titulo_documento="Declaração", corpo_html="<p>corpo</p>", data_emissao="30/09/2026",
    )


def test_sem_assinantes_mostra_so_uma_linha_em_branco():
    bloco = _bloco_assinaturas(_renderizar([]))
    assert "<img" not in bloco
    assert "<p>" not in bloco


def test_um_assinante_mostra_imagem_nome_e_cargo():
    html = _renderizar([{"nome": "Isabel Kiala", "cargo": "Diretora", "data_uri": "data:image/png;base64,ZmFrZQ=="}])
    assert '<img class="assinatura-imagem" src="data:image/png;base64,ZmFrZQ==">' in html
    assert "<p>Isabel Kiala</p>" in html
    assert "<p>Diretora</p>" in html


def test_assinante_sem_imagem_propria_mostra_so_linha_nome_e_cargo():
    html = _renderizar([{"nome": "Ana Silva", "cargo": "Diretora Geral", "data_uri": None}])
    assert "<img" not in html
    assert "<p>Ana Silva</p>" in html
    assert "<p>Diretora Geral</p>" in html


def test_dois_assinantes_lado_a_lado():
    bloco = _bloco_assinaturas(_renderizar([
        {"nome": "Ana Silva", "cargo": "Diretora Geral", "data_uri": None},
        {"nome": "João Pedro", "cargo": "Diretor Pedagógico", "data_uri": None},
    ]))
    assert bloco.count('class="bloco-assinante"') == 2
    assert "<p>Ana Silva</p>" in bloco and "<p>Diretora Geral</p>" in bloco
    assert "<p>João Pedro</p>" in bloco and "<p>Diretor Pedagógico</p>" in bloco
