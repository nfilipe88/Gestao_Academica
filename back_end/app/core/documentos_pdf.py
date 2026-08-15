"""
Geração de PDF para os documentos emitidos pela escola (Solicitações de
Documentos). Gerado sob pedido a partir dos dados da BD — a plataforma
não guarda ficheiros; mesmo o "documento físico com assinatura física"
sai impresso a partir deste mesmo PDF, gerado no momento do pedido.

xhtml2pdf (HTML+CSS -> PDF) foi escolhido por não depender de
bibliotecas nativas fora do Python (ao contrário do WeasyPrint, que
precisa de GTK/Cairo/Pango — problemático no Windows). Jinja2 trata do
escaping dos dados do aluno/escola inseridos no HTML.
"""
import io
from datetime import date, datetime

from jinja2 import Template
from xhtml2pdf import pisa

# Envelope comum a todos os documentos: cabeçalho com o nome da escola,
# rodapé com data de emissão e um espaço para assinatura/carimbo.
_ENVELOPE = Template("""
<html>
<head>
<style>
  @page { size: A4; margin: 2.5cm 2cm; }
  body { font-family: Helvetica, Arial, sans-serif; color: #1e293b; font-size: 12pt; line-height: 1.6; }
  .cabecalho { text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 28px; }
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
    <h1>{{ escola_nome }}</h1>
    <p>{{ escola_razao_social }}{% if escola_nif %} — NIF {{ escola_nif }}{% endif %}</p>
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
    "OUTRO": _corpo_outro,
}


def gerar_pdf_documento(tipo_documento: str, escola: dict, contexto: dict) -> bytes:
    """
    escola: {"nome": ..., "razao_social": ..., "nif": ...}
    contexto: dados específicos do tipo de documento (ver cada _corpo_*).
    """
    gerador_corpo = _GERADORES_CORPO.get(tipo_documento, _corpo_outro)
    corpo_html = gerador_corpo(contexto)

    hoje = date.today() if not isinstance(contexto.get("data_emissao"), (date, datetime)) else contexto["data_emissao"]
    html_final = _ENVELOPE.render(
        escola_nome=escola.get("nome") or "",
        escola_razao_social=escola.get("razao_social") or "",
        escola_nif=escola.get("nif") or "",
        titulo_documento=_TITULOS.get(tipo_documento, "Documento Escolar"),
        corpo_html=corpo_html,
        data_emissao=hoje.strftime("%d/%m/%Y") if isinstance(hoje, date) else str(hoje),
    )

    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(io.StringIO(html_final), dest=buffer)
    if resultado.err:
        raise RuntimeError(f"Falha ao gerar o PDF do documento ({tipo_documento}).")
    return buffer.getvalue()
