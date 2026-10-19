"""
Validação de ficheiros enviados pelos utilizadores pelo CONTEÚDO real,
não pelo tipo que o browser declara (o `Content-Type` de cada parte de
um upload é escolhido livremente por quem envia — um script consegue
mandar um .html a dizer "image/png").

Cada upload passa por `validar_upload`, que identifica o formato pelos
primeiros bytes ("magic numbers") e devolve o tipo REAL — é esse que
fica gravado e com que o ficheiro volta a ser servido, nunca o
declarado. Um formato que não se consegue identificar é recusado.

Ver também `cabecalhos_download` — como servir de volta um ficheiro
enviado por um utilizador sem que o browser o interprete como página da
própria plataforma.
"""
import io
import re
import unicodedata
import zipfile
from urllib.parse import quote

from fastapi import HTTPException

from app.core import eventos_seguranca

PNG = "image/png"
JPEG = "image/jpeg"
GIF = "image/gif"
WEBP = "image/webp"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
ODT = "application/vnd.oasis.opendocument.text"
ODS = "application/vnd.oasis.opendocument.spreadsheet"
DOC = "application/msword"
XLS = "application/vnd.ms-excel"
PPT = "application/vnd.ms-powerpoint"

IMAGENS = {PNG, JPEG, GIF, WEBP}
DOCUMENTOS_OFFICE = {DOCX, XLSX, PPTX, ODT, ODS, DOC, XLS, PPT}

# Os únicos tipos que um browser pode abrir "inline" sem risco: nenhum
# deles executa scripts no contexto do site. Tudo o resto é sempre
# servido como transferência (Content-Disposition: attachment).
TIPOS_SEGUROS_INLINE = IMAGENS | {PDF}

# Um .xlsx/.docx é um ZIP — uns poucos KB comprimidos podem expandir
# para GB ("zip bomb") e esgotar a memória do servidor ao abri-lo.
_MAXIMO_DESCOMPRIMIDO = 100 * 1024 * 1024  # 100 MB
_MAXIMO_RACIO_COMPRESSAO = 200

_EXTENSOES_OLE = {"doc": DOC, "xls": XLS, "ppt": PPT}


class _ZipBomba(Exception):
    pass


def _tipo_zip(conteudo: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
            membros = arquivo.infolist()
            total = sum(m.file_size for m in membros)
            comprimido = max(sum(m.compress_size for m in membros), 1)
            if total > _MAXIMO_DESCOMPRIMIDO or total / comprimido > _MAXIMO_RACIO_COMPRESSAO:
                raise _ZipBomba()
            nomes = {m.filename for m in membros}
            if "[Content_Types].xml" in nomes:
                if any(n.startswith("xl/") for n in nomes):
                    return XLSX
                if any(n.startswith("word/") for n in nomes):
                    return DOCX
                if any(n.startswith("ppt/") for n in nomes):
                    return PPTX
            if "mimetype" in nomes:
                mimetype = arquivo.read("mimetype")[:100].decode("ascii", "ignore").strip()
                if mimetype in {ODT, ODS}:
                    return mimetype
    except zipfile.BadZipFile:
        return None
    return None


def detetar_tipo(conteudo: bytes, nome_ficheiro: str = "") -> str | None:
    """Tipo real do ficheiro pelos primeiros bytes, ou None se não for
    nenhum dos formatos que a plataforma aceita em algum lado."""
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if conteudo.startswith(b"\xff\xd8\xff"):
        return JPEG
    if conteudo[:6] in (b"GIF87a", b"GIF89a"):
        return GIF
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return WEBP
    # A especificação PDF tolera lixo antes do cabeçalho (até 1 KB).
    if b"%PDF-" in conteudo[:1024]:
        return PDF
    if conteudo.startswith(b"PK\x03\x04"):
        return _tipo_zip(conteudo)
    if conteudo.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        # Formato binário antigo do Office (OLE): o mesmo contentor para
        # .doc/.xls/.ppt — a extensão só serve para escolher qual dos três,
        # nunca deixa passar outro formato.
        extensao = nome_ficheiro.rsplit(".", 1)[-1].lower() if "." in nome_ficheiro else ""
        return _EXTENSOES_OLE.get(extensao)
    return None


# Conteúdo que nunca é um documento legítimo num upload desta plataforma:
# páginas/scripts (o ataque do anexo .html), executáveis Windows/Linux,
# scripts de shell e PHP — quase sempre disfarçados com outra extensão.
_INICIOS_MALICIOSOS = re.compile(
    rb"^(\xef\xbb\xbf)?\s*(<\s*(!doctype|html|script|svg|iframe|\?php|\?xml)|MZ|\x7fELF|#!)", re.IGNORECASE
)


async def validar_upload(conteudo: bytes, aceites: set[str], descricao_aceites: str, nome_ficheiro: str = "") -> str:
    """Devolve o tipo REAL do ficheiro (é esse que se grava e com que se
    serve depois), ou 400 se não for um dos `aceites`. Um ficheiro
    malicioso (página/script/executável disfarçado, zip bomb) fica
    registado como evento de segurança, com o IP e o utilizador; um
    engano honesto (ex.: um PDF onde se pede uma foto) não."""
    try:
        tipo = detetar_tipo(conteudo, nome_ficheiro)
    except _ZipBomba:
        await eventos_seguranca.registar(
            eventos_seguranca.FICHEIRO_MALICIOSO, eventos_seguranca.ALTA,
            f'"{nome_ficheiro}": ficheiro comprimido que expande para um tamanho anormal (zip bomb).',
        )
        raise HTTPException(status_code=400, detail="Ficheiro recusado: o conteúdo comprimido é anormalmente grande.")
    if tipo is None and _INICIOS_MALICIOSOS.match(conteudo[:256]):
        await eventos_seguranca.registar(
            eventos_seguranca.FICHEIRO_MALICIOSO, eventos_seguranca.ALTA,
            f'"{nome_ficheiro}": conteúdo de página/script/executável enviado como documento.',
        )
    if tipo not in aceites:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não aceite — o conteúdo do ficheiro não corresponde a um formato válido. Use {descricao_aceites}."
        )
    return tipo


def _nome_ascii(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    base = "".join(c for c in base if c.isalnum() or c in " ._-()").strip()
    return base or "ficheiro"


def cabecalhos_download(nome_original: str, content_type: str) -> tuple[str, dict]:
    """(media_type, cabeçalhos) para devolver um ficheiro enviado por um
    utilizador. Só imagens e PDF abrem no browser; qualquer outro tipo
    (incluindo registos antigos gravados com o tipo declarado, de antes
    desta validação existir) é servido como transferência binária — um
    .html nunca é interpretado como página da plataforma. O nome vai
    codificado (RFC 6266/5987): aspas ou quebras de linha no nome
    original não alteram o cabeçalho."""
    seguro = content_type in TIPOS_SEGUROS_INLINE
    media_type = content_type if seguro else "application/octet-stream"
    disposicao = "inline" if seguro else "attachment"
    cabecalhos = {
        "Content-Disposition": f"{disposicao}; filename=\"{_nome_ascii(nome_original)}\"; filename*=UTF-8''{quote(nome_original, safe='')}",
        "X-Content-Type-Options": "nosniff",
    }
    return media_type, cabecalhos
