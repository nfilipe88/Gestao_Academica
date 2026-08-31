"""
Geração de PDF para os documentos emitidos pela escola (Solicitações de
Documentos). Gerado sob pedido a partir dos dados da BD — a plataforma
não guarda ficheiros; mesmo o "documento físico com assinatura física"
sai impresso a partir deste mesmo PDF, gerado no momento do pedido.

xhtml2pdf (HTML+CSS -> PDF) foi escolhido por não depender de
bibliotecas nativas fora do Python (ao contrário do WeasyPrint, que
precisa de GTK/Cairo/Pango — problemático no Windows). Jinja2 trata do
escaping dos dados do aluno/escola inseridos no HTML.

Personalização por escola (TemplateDocumentoPersonalizado, ver
app/database/models_documentos.py): cada tenant pode substituir o
"corpo" de um tipo de documento pelo seu próprio HTML/CSS — o
cabeçalho/rodapé/assinatura do envelope continuam normalizados. Esse
HTML vem de um Gestor, não do código-fonte, por isso é renderizado
numa SandboxedEnvironment do Jinja2 em vez do Template() normal usado
pelos corpos nativos abaixo: sem sandbox, um template malicioso como
`{{ self.__init__.__globals__ }}` conseguiria alcançar objetos internos
do processo (Server-Side Template Injection). A SandboxedEnvironment
bloqueia o acesso a atributos "perigosos" (dunder, __class__, etc.) e
levanta SecurityError nesses casos.
"""
import io
import logging
from datetime import date, datetime

from jinja2 import Template
from jinja2.sandbox import SandboxedEnvironment
from xhtml2pdf import pisa

logger = logging.getLogger("documentos_pdf")

# autoescape=True: o corpo_html do tenant é tratado como o "shell" do
# template (pode conter as suas próprias tags HTML), mas qualquer
# {{ variavel }} interpolada continua escapada — evita que um valor
# vindo da BD (ex.: nome de aluno com "<script>") seja interpretado
# como HTML dentro do próprio corpo personalizado.
_AMBIENTE_SEGURO = SandboxedEnvironment(autoescape=True)

# Envelope comum a todos os documentos: cabeçalho com o nome da escola,
# rodapé com data de emissão e um espaço para assinatura/carimbo.
_ENVELOPE = Template("""
<html>
<head>
<style>
  @page { size: A4; margin: 2.5cm 2cm; }
  body { font-family: Helvetica, Arial, sans-serif; color: #1e293b; font-size: 12pt; line-height: 1.6; }
  .cabecalho { text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 28px; }
  .cabecalho img.logotipo { max-height: 60px; max-width: 200px; margin-bottom: 8px; }
  .cabecalho h1 { color: #2563eb; font-size: 16pt; margin: 0 0 4px 0; }
  .cabecalho p { color: #64748b; font-size: 9pt; margin: 0; }
  .titulo-documento { text-align: center; font-size: 14pt; font-weight: bold; text-transform: uppercase; margin: 24px 0; letter-spacing: 1px; }
  .corpo { text-align: justify; margin-bottom: 40px; }
  table.dados { width: 100%; border-collapse: collapse; margin: 16px 0; }
  table.dados td { padding: 4px 0; font-size: 11pt; }
  table.dados td.rotulo { color: #64748b; width: 180px; }
  table.notas { width: 100%; border-collapse: collapse; margin: 16px 0; }
  table.notas th, table.notas td { border: 1px solid #cbd5e1; padding: 6px 8px; font-size: 10pt; text-align: left; }
  table.notas th { background: #f1f5f9; }
  .assinatura { margin-top: 60px; text-align: center; }
  .assinatura .linha { border-top: 1px solid #1e293b; width: 280px; margin: 0 auto 6px auto; }
  .rodape { position: fixed; bottom: -1.5cm; left: 0; right: 0; text-align: center; font-size: 8pt; color: #94a3b8; }
</style>
</head>
<body>
  <div class="cabecalho">
    {% if escola_logo_data_uri %}<img class="logotipo" src="{{ escola_logo_data_uri }}">{% endif %}
    <h1>{{ escola_nome }}</h1>
    <p>{{ escola_razao_social }}{% if escola_nif %} — NIF {{ escola_nif }}{% endif %}</p>
    {% if escola_morada %}<p>{{ escola_morada }}</p>{% endif %}
    {% if escola_contacto %}<p>{{ escola_contacto }}</p>{% endif %}
  </div>

  <div class="titulo-documento">{{ titulo_documento }}</div>

  <div class="corpo">
    {{ corpo_html | safe }}
  </div>

  <div class="assinatura">
    <div class="linha"></div>
    <p>{{ escola_nome }}</p>
  </div>

  <div class="rodape">Documento emitido eletronicamente em {{ data_emissao }} — SaaS Gestão Académica</div>
</body>
</html>
""")

_TITULOS = {
    "CERTIFICADO": "Certificado de Frequência",
    "DECLARACAO": "Declaração",
    "HISTORICO_ESCOLAR": "Histórico Escolar",
    "BOLETIM": "Boletim de Notas",
    "RECIBO": "Recibo de Pagamento",
    "OUTRO": "Documento Escolar",
}


def _corpo_certificado(contexto: dict) -> str:
    return Template("""
      <p>Para os devidos efeitos, certifica-se que <strong>{{ aluno_nome }}</strong>,
      {% if numero_documento %}portador(a) do documento de identificação n.º {{ numero_documento }},{% endif %}
      se encontra matriculado(a) nesta instituição de ensino{% if turma_nome %} na turma <strong>{{ turma_nome }}</strong>{% endif %}{% if ano_letivo %}, no ano letivo de {{ ano_letivo }}{% endif %}.</p>
    """).render(**contexto)


def _corpo_declaracao(contexto: dict) -> str:
    return Template("""
      <p>Declara-se, para os devidos efeitos, que <strong>{{ aluno_nome }}</strong>
      {% if numero_documento %}(documento de identificação n.º {{ numero_documento }}){% endif %}
      é aluno(a) desta instituição de ensino{% if turma_nome %}, encontrando-se inscrito(a) na turma <strong>{{ turma_nome }}</strong>{% endif %}{% if ano_letivo %} no ano letivo de {{ ano_letivo }}{% endif %}.</p>
    """).render(**contexto)


def _corpo_historico_escolar(contexto: dict) -> str:
    return Template("""
      <table class="dados">
        <tr><td class="rotulo">Aluno(a)</td><td>{{ aluno_nome }}</td></tr>
        {% if numero_documento %}<tr><td class="rotulo">Documento</td><td>{{ numero_documento }}</td></tr>{% endif %}
        {% if data_nascimento %}<tr><td class="rotulo">Data de nascimento</td><td>{{ data_nascimento }}</td></tr>{% endif %}
      </table>

      {% for ano in anos %}
        <p><strong>Ano letivo {{ ano.ano_letivo }}</strong> — Turma {{ ano.turma_nome or '—' }} ({{ ano.status_matricula }})</p>
        <table class="notas">
          <tr><th>Disciplina</th><th>Período</th><th>Nota</th></tr>
          {% for linha in ano.notas %}
            <tr><td>{{ linha.disciplina }}</td><td>{{ linha.periodo or '—' }}</td><td>{{ linha.valor if linha.valor is not none else '—' }}</td></tr>
          {% else %}
            <tr><td colspan="3">Sem registo de notas.</td></tr>
          {% endfor %}
        </table>
      {% else %}
        <p>Sem histórico de matrículas registado.</p>
      {% endfor %}
    """).render(**contexto)


def _corpo_boletim(contexto: dict) -> str:
    return Template("""
      <table class="dados">
        <tr><td class="rotulo">Aluno(a)</td><td>{{ aluno_nome }}</td></tr>
        <tr><td class="rotulo">Turma</td><td>{{ turma_nome or '—' }}</td></tr>
        <tr><td class="rotulo">Ano letivo</td><td>{{ ano_letivo or '—' }}</td></tr>
      </table>
      <table class="notas">
        <tr><th>Disciplina</th><th>Período</th><th>Tipo</th><th>Nota</th></tr>
        {% for linha in notas %}
          <tr><td>{{ linha.disciplina }}</td><td>{{ linha.periodo or '—' }}</td><td>{{ linha.tipo or '—' }}</td><td>{{ linha.valor if linha.valor is not none else '—' }}</td></tr>
        {% else %}
          <tr><td colspan="4">Sem registo de notas.</td></tr>
        {% endfor %}
      </table>
    """).render(**contexto)


def _corpo_recibo(contexto: dict) -> str:
    # "Recibo de Pagamento", nunca "Fatura" — este documento não é
    # emitido por software certificado pela AGT (ver
    # cruds/financeiro.py::Recibo), por isso não tem o mesmo valor
    # fiscal de uma fatura; a nota no rodapé deixa isso explícito em
    # vez de deixar a escola/o responsável presumir o contrário.
    return Template("""
      <table class="dados">
        <tr><td class="rotulo">Recibo N.º</td><td>{{ numero_recibo }}</td></tr>
        <tr><td class="rotulo">Data de emissão</td><td>{{ data_emissao }}</td></tr>
        <tr><td class="rotulo">Pago por</td><td>{{ nome_pagador }}{% if numero_documento_pagador %} — doc. n.º {{ numero_documento_pagador }}{% endif %}</td></tr>
        <tr><td class="rotulo">Referente a</td><td>{{ aluno_nome }} — {{ descricao }}</td></tr>
        <tr><td class="rotulo">Forma de pagamento</td><td>{{ forma_pagamento }}</td></tr>
        <tr><td class="rotulo">Valor recebido</td><td><strong>{{ valor }} {{ moeda }}</strong></td></tr>
      </table>
      <p style="margin-top: 28px; font-size: 9pt; color: #94a3b8;">
        Este documento é um recibo de pagamento, emitido pela plataforma de gestão da escola —
        não é uma fatura fiscal certificada.
      </p>
    """).render(**contexto)


def _corpo_outro(contexto: dict) -> str:
    return Template("""
      <table class="dados">
        <tr><td class="rotulo">Aluno(a)</td><td>{{ aluno_nome }}</td></tr>
      </table>
      <p>{{ descricao }}</p>
    """).render(**contexto)


_GERADORES_CORPO = {
    "CERTIFICADO": _corpo_certificado,
    "DECLARACAO": _corpo_declaracao,
    "HISTORICO_ESCOLAR": _corpo_historico_escolar,
    "BOLETIM": _corpo_boletim,
    "RECIBO": _corpo_recibo,
    "OUTRO": _corpo_outro,
}


def renderizar_corpo_personalizado(corpo_html_personalizado: str, contexto: dict) -> str:
    """
    Renderiza o corpo_html de um TemplateDocumentoPersonalizado com os
    dados reais/de amostra do documento. Lançada para fora tal-e-qual
    (TemplateSyntaxError, SecurityError, UndefinedError, ...) — quem
    chama decide se isso é um erro fatal (guardar/pré-visualizar, onde
    o Gestor tem de corrigir o template) ou algo a ignorar com
    fallback (gerar_pdf_documento, na emissão real de um documento já
    pago, ver abaixo).
    """
    return _AMBIENTE_SEGURO.from_string(corpo_html_personalizado).render(**contexto)


def gerar_pdf_documento(
    tipo_documento: str, escola: dict, contexto: dict,
    corpo_html_personalizado: str | None = None, exigir_personalizado: bool = False
) -> bytes:
    """
    escola: {"nome": ..., "razao_social": ..., "nif": ..., "morada": ..., "contacto": ...,
             "logo_data_uri": data:image/...;base64,... ou None (ver app/core/storage.py::obter_logo_data_uri)}
    contexto: dados específicos do tipo de documento (ver cada _corpo_*).
    corpo_html_personalizado: se o tenant tiver um layout próprio ativo
    para este tipo_documento (ver cruds/documentos.py), substitui o
    corpo nativo.
    exigir_personalizado: False (default, usado na emissão real de um
    documento já pago) — uma falha a renderizar o template do tenant
    NUNCA deve impedir o download; cai silenciosamente para o corpo
    padrão da plataforma (fica registado nos logs para o suporte poder
    avisar a escola). True (usado ao guardar/pré-visualizar) — o Gestor
    tem de ver o erro real para poder corrigir o template, por isso a
    exceção é propagada em vez de escondida atrás de um fallback.
    """
    corpo_html = None
    if corpo_html_personalizado:
        try:
            corpo_html = renderizar_corpo_personalizado(corpo_html_personalizado, contexto)
        except Exception:
            if exigir_personalizado:
                raise
            logger.exception(
                "Falha ao renderizar o template personalizado de '%s' — a usar o layout padrão como reserva.",
                tipo_documento
            )
            corpo_html = None

    if corpo_html is None:
        gerador_corpo = _GERADORES_CORPO.get(tipo_documento, _corpo_outro)
        corpo_html = gerador_corpo(contexto)

    hoje = date.today() if not isinstance(contexto.get("data_emissao"), (date, datetime)) else contexto["data_emissao"]
    html_final = _ENVELOPE.render(
        escola_nome=escola.get("nome") or "",
        escola_razao_social=escola.get("razao_social") or "",
        escola_nif=escola.get("nif") or "",
        escola_morada=escola.get("morada") or "",
        escola_contacto=escola.get("contacto") or "",
        escola_logo_data_uri=escola.get("logo_data_uri"),
        titulo_documento=_TITULOS.get(tipo_documento, "Documento Escolar"),
        corpo_html=corpo_html,
        data_emissao=hoje.strftime("%d/%m/%Y") if isinstance(hoje, date) else str(hoje),
    )

    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(io.StringIO(html_final), dest=buffer)
    if resultado.err:
        raise RuntimeError(f"Falha ao gerar o PDF do documento ({tipo_documento}).")
    return buffer.getvalue()


# ==========================================
# CARTÃO DE ACESSO — fora da família dos documentos formais acima de
# propósito: não é um "documento" que a família pede/paga (ver
# Solicitações de Documentos), é um crachá operacional que a escola
# emite diretamente (ver cruds/alunos.py::gerar_cartao_acesso). Por
# isso não usa o _ENVELOPE (folha A4, assinatura, tom de carta formal).
#
# Ainda assim é PERSONALIZÁVEL por escola, tal como os documentos
# formais (ver TemplateDocumentoPersonalizado/TIPOS_DOCUMENTO_PERSONALIZAVEL
# em cruds/documentos.py) — cada escola desenha o seu próprio cartão.
# Só o tamanho físico da página (_CARTAO_ENVELOPE_FIXO, formato CR80 —
# o mesmo de um cartão bancário) fica fora do alcance do template do
# tenant, para nunca sair um PDF que não caiba numa impressora/
# plastificadora de cartões; todo o resto (cores, disposição, se
# mostra ou não a foto) é livre.
# ==========================================
_CARTAO_ENVELOPE_FIXO = Template("""
<html>
<head>
<style>
  @page { size: 85.6mm 54mm; margin: 0; }
  body { margin: 0; padding: 0; font-family: Helvetica, Arial, sans-serif; }
</style>
</head>
<body>{{ corpo_html | safe }}</body>
</html>
""")

# Layout nativo (o que sai se a escola nunca personalizar). Três
# armadilhas do xhtml2pdf foram encontradas e contornadas ao imprimir
# um cartão real para conferir o resultado — deixadas documentadas
# aqui porque não são óbvias e voltam a morder se alguém "arrumar" este
# HTML sem saber porque está assim:
#   1) `.cartao` NUNCA pode ter `height` explícito — combinado com uma
#      <table> lá dentro, o conteúdo a mais transborda para uma SEGUNDA
#      página (o cartão sai partido em duas folhas) em vez de cortar.
#      A altura de 54mm já vem do @page; a div não precisa de a repetir.
#   2) A <table> tem de ter exatamente UMA linha (<tr>). Uma segunda
#      linha (e até um <p> como IRMÃO da table, fora dela) faz o
#      xhtml2pdf tratar o conteúdo como blocos separados, cada um a
#      reaplicar sozinho o border/padding do "envelope" — o cartão sai
#      com a moldura azul cortada a meio, como duas caixas empilhadas.
#   3) Dentro da célula de texto, várias tags <p> (uma por linha) sofrem
#      de um espaçamento vertical enorme que as margens/line-height por
#      CSS não conseguem anular. A correção é escrever tudo como UM só
#      bloco de texto com <br> a separar as linhas (em vez de <p> por
#      linha) — problema desaparece por completo.
# Testado com e sem foto, com e sem logótipo — ver histórico desta
# sessão para as capturas de ecrã que motivaram cada uma destas regras.
_CARTAO_ACESSO_CORPO_NATIVO = Template("""
<style>
  .cartao { width: 85.6mm; padding: 3mm; box-sizing: border-box; border: 0.4mm solid #2563eb; }
  table.layout { width: 100%; border-collapse: collapse; }
  table.layout td { border: none; padding: 0; vertical-align: top; }
  td.foto-col { width: 21mm; }
  td.dados-col { padding-left: 3mm; font-size: 7pt; line-height: 1.35; color: #475569; }
  .foto { width: 19mm; height: 23mm; }
  .foto-vazia {
    display: block; width: 18.4mm; height: 22.4mm; border: 0.3mm dashed #cbd5e1; text-align: center;
    font-size: 6pt; color: #94a3b8; padding-top: 8mm;
  }
  .escola-nome { font-size: 8pt; font-weight: bold; color: #2563eb; }
  .rotulo-cartao { font-size: 6pt; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }
  .aluno-nome { font-size: 9pt; font-weight: bold; color: #1e293b; }
  .rotulo-dado { color: #94a3b8; }
  .rodape { font-size: 5.5pt; color: #94a3b8; }
</style>
<div class="cartao">
  <table class="layout">
    <tr>
      <td class="foto-col">
        {% if foto_data_uri %}<img class="foto" src="{{ foto_data_uri }}">{% else %}<span class="foto-vazia">Sem<br>fotografia</span>{% endif %}
      </td>
      <td class="dados-col">
        {% if escola_logo_data_uri %}<img src="{{ escola_logo_data_uri }}" style="max-height:6mm;max-width:30mm;"><br>{% endif %}
        <span class="escola-nome">{{ escola_nome }}</span><br>
        <span class="rotulo-cartao">Cartão de Acesso</span><br><br>
        <span class="aluno-nome">{{ aluno_nome }}</span><br>
        <span class="rotulo-dado">Matrícula:</span> {{ matricula_interna }}<br>
        <span class="rotulo-dado">Turma:</span> {{ turma_nome or '—' }}<br>
        <span class="rotulo-dado">Ano letivo:</span> {{ ano_letivo or '—' }}<br>
        <span class="rodape">Emitido em {{ data_emissao }}</span>
      </td>
    </tr>
  </table>
</div>
""")


def _corpo_cartao_acesso(escola: dict, dados: dict, corpo_html_personalizado: str | None, exigir_personalizado: bool) -> str:
    """dados: {"aluno_nome", "matricula_interna", "turma_nome" (opcional),
    "ano_letivo" (opcional), "foto_data_uri" (opcional — sem foto ativa,
    mostra um espaço reservado em vez de bloquear a emissão)}.

    corpo_html_personalizado/exigir_personalizado: mesmo contrato de
    gerar_pdf_documento acima — False (emissão real) nunca deixa um
    template de tenant partido bloquear o cartão, cai em silêncio para
    o layout nativo; True (guardar/pré-visualizar, ver cruds/documentos.py)
    propaga o erro para o Gestor poder corrigir. Extraído da função de
    UM cartão para ser reaproveitado também no lote (vários cartões,
    um por página, no mesmo PDF — ver gerar_pdf_cartoes_acesso_lote)."""
    contexto = {
        "escola_nome": escola.get("nome") or "",
        "escola_logo_data_uri": escola.get("logo_data_uri"),
        "aluno_nome": dados.get("aluno_nome") or "",
        "matricula_interna": dados.get("matricula_interna") or "",
        "turma_nome": dados.get("turma_nome"),
        "ano_letivo": dados.get("ano_letivo"),
        "foto_data_uri": dados.get("foto_data_uri"),
        "data_emissao": date.today().strftime("%d/%m/%Y"),
    }

    if corpo_html_personalizado:
        try:
            return renderizar_corpo_personalizado(corpo_html_personalizado, contexto)
        except Exception:
            if exigir_personalizado:
                raise
            logger.exception("Falha ao renderizar o cartão de acesso personalizado — a usar o layout nativo como reserva.")

    return _CARTAO_ACESSO_CORPO_NATIVO.render(**contexto)


def gerar_pdf_cartao_acesso(
    escola: dict, dados: dict, corpo_html_personalizado: str | None = None, exigir_personalizado: bool = False
) -> bytes:
    corpo_html = _corpo_cartao_acesso(escola, dados, corpo_html_personalizado, exigir_personalizado)
    html_final = _CARTAO_ENVELOPE_FIXO.render(corpo_html=corpo_html)
    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(io.StringIO(html_final), dest=buffer)
    if resultado.err:
        raise RuntimeError("Falha ao gerar o PDF do cartão de acesso.")
    return buffer.getvalue()


def gerar_pdf_cartoes_acesso_lote(escola: dict, lista_dados: list[dict], corpo_html_personalizado: str | None = None) -> bytes:
    """Vários cartões, um por página, no MESMO PDF — para a Secretaria
    imprimir de uma vez os cartões de uma turma inteira (o caso de uso
    real: início do ano letivo), em vez de aluno a aluno pelo ecrã de
    Alunos. Cada cartão reaproveita exatamente o mesmo bloco HTML já
    validado no cartão individual (_corpo_cartao_acesso), só separado
    por um <div style="page-break-before:always"> — testado a repetir
    esse bloco isolado várias vezes: como cada um já é, sozinho, a
    unidade "segura" descoberta ao corrigir o cartão individual (ver
    comentário em _CARTAO_ACESSO_CORPO_NATIVO), repeti-lo não introduz
    nenhuma armadilha nova, ao contrário de tentar pôr vários cartões
    lado a lado numa grelha na mesma página (não tentado, arriscado à
    luz dessas mesmas armadilhas).

    exigir_personalizado é sempre False aqui: mesmo que o template da
    escola esteja provisoriamente partido, o lote nunca deve falhar a
    meio — cada cartão cai para o nativo silenciosamente, como na
    emissão individual."""
    if not lista_dados:
        raise ValueError("Lista de cartões vazia.")

    partes = []
    for i, dados in enumerate(lista_dados):
        if i > 0:
            partes.append('<div style="page-break-before: always;"></div>')
        partes.append(_corpo_cartao_acesso(escola, dados, corpo_html_personalizado, exigir_personalizado=False))

    html_final = _CARTAO_ENVELOPE_FIXO.render(corpo_html="".join(partes))
    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(io.StringIO(html_final), dest=buffer)
    if resultado.err:
        raise RuntimeError("Falha ao gerar o PDF dos cartões de acesso em lote.")
    return buffer.getvalue()


# ==========================================
# RELATÓRIO DE INDICADORES (BI) — folha A4 normal, sem restrição de
# tamanho como o cartão (nem os problemas de renderização que isso
# trazia, ver acima): é o mesmo tipo de tabela HTML simples já provado
# a funcionar bem no Histórico Escolar em app/cruds/documentos.py, só
# que aqui várias secções em vez de uma. Não personalizável por escola
# de propósito — é um relatório de gestão interna, não um documento com
# a identidade da escola que a família vê (ver cruds/indicadores.py::
# gerar_pdf_relatorio); não passa por TIPOS_DOCUMENTO/
# TemplateDocumentoPersonalizado.
# ==========================================
_RELATORIO_INDICADORES = Template("""
<html>
<head>
<style>
  @page { size: A4; margin: 2cm; }
  body { font-family: Helvetica, Arial, sans-serif; color: #1e293b; font-size: 10pt; line-height: 1.5; }
  .cabecalho { text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 10px; margin-bottom: 20px; }
  .cabecalho img.logotipo { max-height: 50px; max-width: 180px; margin-bottom: 6px; }
  .cabecalho h1 { color: #2563eb; font-size: 15pt; margin: 0 0 3px 0; }
  .cabecalho p { color: #64748b; font-size: 8pt; margin: 0; }
  h2.secao { font-size: 11pt; color: #1e293b; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; margin: 18px 0 8px 0; }
  table.dados { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
  table.dados th, table.dados td { border: 1px solid #cbd5e1; padding: 5px 7px; font-size: 8.5pt; text-align: left; }
  table.dados th { background: #f1f5f9; }
  table.kpis { width: 100%; border-collapse: collapse; }
  table.kpis td { border: none; padding: 5px 14px 5px 0; font-size: 9pt; }
  table.kpis td.rotulo { color: #64748b; white-space: nowrap; }
  table.kpis td.valor { font-weight: bold; font-size: 11pt; color: #1e293b; }
  .legenda { font-size: 8pt; color: #64748b; margin: 0 0 10px 0; }
  .rodape { position: fixed; bottom: -1.3cm; left: 0; right: 0; text-align: center; font-size: 7pt; color: #94a3b8; }
</style>
</head>
<body>
  <div class="cabecalho">
    {% if escola_logo_data_uri %}<img class="logotipo" src="{{ escola_logo_data_uri }}">{% endif %}
    <h1>{{ escola_nome }}</h1>
    <p>Relatório de Indicadores — gerado em {{ data_emissao }}</p>
  </div>

  <h2 class="secao">Resumo</h2>
  <table class="kpis">
    <tr>
      <td class="rotulo">Alunos ativos</td><td class="valor">{{ total_alunos_ativos }}</td>
      <td class="rotulo">Ocupação de vagas</td><td class="valor">{{ taxa_ocupacao_geral }}%</td>
    </tr>
    <tr>
      <td class="rotulo">Inadimplência</td><td class="valor">{{ taxa_inadimplencia }}%</td>
      <td class="rotulo">Receita do mês</td><td class="valor">{{ receita_recebida_mes_atual }} {{ moeda }}</td>
    </tr>
    <tr>
      <td class="rotulo">Conversão CRM</td><td class="valor">{{ taxa_conversao }}%</td>
      <td class="rotulo">Risco de evasão alto</td><td class="valor">{{ risco_total_alto }}</td>
    </tr>
  </table>

  <h2 class="secao">Ocupação por turma</h2>
  <table class="dados">
    <tr><th>Turma</th><th>Matriculados</th><th>Vagas</th><th>Ocupação</th></tr>
    {% for t in ocupacao_por_turma %}
    <tr><td>{{ t.nome_turma }}</td><td>{{ t.matriculados }}</td><td>{{ t.vagas_maximas }}</td><td>{{ t.taxa_ocupacao }}%</td></tr>
    {% else %}
    <tr><td colspan="4">Nenhuma turma registada.</td></tr>
    {% endfor %}
  </table>

  <h2 class="secao">Desempenho médio por turma</h2>
  <table class="dados">
    <tr><th>Turma</th><th>Média</th><th>Alunos avaliados</th></tr>
    {% for t in desempenho_por_turma %}
    <tr><td>{{ t.nome_turma }}</td><td>{{ t.media if t.media is not none else '—' }}</td><td>{{ t.total_alunos_avaliados }}</td></tr>
    {% else %}
    <tr><td colspan="3">Ainda não há notas lançadas.</td></tr>
    {% endfor %}
  </table>

  <h2 class="secao">Financeiro</h2>
  <table class="kpis">
    <tr>
      <td class="rotulo">Faturas em aberto</td><td class="valor">{{ total_faturas_em_aberto }}</td>
      <td class="rotulo">Faturas atrasadas</td><td class="valor">{{ total_faturas_atrasadas }}</td>
    </tr>
    <tr>
      <td class="rotulo">Valor total em atraso</td><td class="valor">{{ valor_total_em_atraso }} {{ moeda }}</td>
      <td class="rotulo">Contratos ativos</td><td class="valor">{{ total_contratos_ativos }}</td>
    </tr>
  </table>

  <h2 class="secao">Funil do CRM</h2>
  <table class="dados">
    <tr><th>Etapa</th><th>Total</th><th>Ganho?</th></tr>
    {% for e in funil_crm %}
    <tr><td>{{ e.nome_etapa }}</td><td>{{ e.total }}</td><td>{{ 'Sim' if e.eh_etapa_ganho else '—' }}</td></tr>
    {% else %}
    <tr><td colspan="3">Nenhuma etapa configurada.</td></tr>
    {% endfor %}
  </table>
  <p class="legenda">{{ total_leads }} lead(s) no total · {{ total_convertidos }} convertido(s)</p>

  <h2 class="secao">Eficiência por Objetivo de Aprendizagem</h2>
  <table class="dados">
    <tr><th>Disciplina</th><th>Objetivo</th><th>Média objetivo</th><th>Média disciplina</th><th>Notas</th></tr>
    {% for o in eficiencia_por_objetivo %}
    <tr>
      <td>{{ o.nome_disciplina }}</td>
      <td>{{ o.nome_objetivo }}{% if o.abaixo_da_media %} (abaixo da média){% endif %}</td>
      <td>{{ o.media_objetivo }}</td>
      <td>{{ o.media_disciplina if o.media_disciplina is not none else '—' }}</td>
      <td>{{ o.total_notas }}</td>
    </tr>
    {% else %}
    <tr><td colspan="5">Ainda não há avaliações ligadas a um objetivo de aprendizagem.</td></tr>
    {% endfor %}
  </table>

  <h2 class="secao">Risco de Evasão</h2>
  <p class="legenda">Pontuação por regras a partir de faltas, queda no rendimento e mensalidades em atraso — não é um modelo de IA.</p>
  <table class="dados">
    <tr><th>Aluno</th><th>Turma</th><th>Nível</th><th>Pontuação</th><th>Fatores</th></tr>
    {% for a in risco_evasao %}
    <tr><td>{{ a.nome_aluno }}</td><td>{{ a.nome_turma }}</td><td>{{ a.nivel_risco }}</td><td>{{ a.pontuacao_risco }}</td><td>{{ a.fatores | join(', ') }}</td></tr>
    {% else %}
    <tr><td colspan="5">Nenhum aluno com sinais de risco no momento.</td></tr>
    {% endfor %}
  </table>

  <div class="rodape">Relatório gerado eletronicamente em {{ data_emissao }} — SaaS Gestão Académica</div>
</body>
</html>
""")


def gerar_pdf_relatorio_indicadores(escola: dict, contexto: dict) -> bytes:
    """escola: {"nome", "logo_data_uri"}. contexto: ver
    cruds/indicadores.py::gerar_pdf_relatorio para a forma completa
    (achatada — sem aninhamento "academico"/"financeiro"/"crm" como no
    payload da API, para o template não precisar de repetir prefixos)."""
    html = _RELATORIO_INDICADORES.render(
        escola_nome=escola.get("nome") or "",
        escola_logo_data_uri=escola.get("logo_data_uri"),
        data_emissao=date.today().strftime("%d/%m/%Y"),
        **contexto,
    )
    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(io.StringIO(html), dest=buffer)
    if resultado.err:
        raise RuntimeError("Falha ao gerar o PDF do relatório de indicadores.")
    return buffer.getvalue()
