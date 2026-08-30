"""
Armazenamento de ficheiros enviados pelo utilizador (logótipo da
escola, anexos de Comunicados) — abstração sobre S3-compatível (AWS
S3, MinIO, etc.) com fallback para disco local em desenvolvimento/
instância única.

Ao contrário dos PDFs gerados (documentos_pdf.py — nunca persistidos,
sempre recriados a pedido a partir dos dados na BD), um ficheiro
realmente enviado pelo utilizador tem de ser guardado algures ENTRE
pedidos — e num deploy com mais de uma instância do back-end (Fase 2,
ver docker-compose.yml), disco local NÃO é esse "algures": cada
instância tem o seu próprio disco, e um redeploy apaga tudo. Por isso
S3-compatível é a escolha por omissão; disco local só é correto com
uma única instância (mesma limitação já documentada para REDIS_URL em
falta — ver rate_limiter.py/lock_distribuido.py).

Isolamento entre escolas: ao contrário das tabelas da BD, um bucket
S3 não sabe aplicar Row-Level Security sozinho. A defesa aqui é dupla:
(1) a chave de cada ficheiro é sempre prefixada por tenant_id
(gerar_chave), e (2) as transferências NUNCA passam por URLs públicas/
pré-assinadas diretas do bucket — sempre por um endpoint autenticado
do back-end que valida tenant_id/RBAC primeiro (ver
app/api/v1/configuracoes.py e app/api/v1/comunicacoes.py) e só depois
chama obter_ficheiro.

boto3 é síncrono — todas as chamadas correm em asyncio.to_thread para
não bloquear o event loop enquanto esperam pela rede.
"""
import asyncio
import base64
import logging
import os
import re
import uuid
from pathlib import Path

logger = logging.getLogger("storage")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL") or None
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

# Só usado quando S3_BUCKET não está definido — pasta local, relativa
# ao diretório de trabalho do processo (no Docker, ver volume dedicado
# no docker-compose.yml de produção; localmente, .gitignore já ignora "uploads/").
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))

_s3_cliente = None
if S3_BUCKET:
    import boto3
    _s3_cliente = boto3.client(
        "s3", endpoint_url=S3_ENDPOINT_URL, region_name=S3_REGION,
        aws_access_key_id=S3_ACCESS_KEY, aws_secret_access_key=S3_SECRET_KEY,
    )
else:
    logger.warning(
        "S3_BUCKET não definido — ficheiros enviados (logótipo, anexos) ficam "
        "em disco local (%s). Só correto com UMA instância do back-end; ver .env.example.",
        UPLOAD_DIR.resolve(),
    )


def _sanitizar_nome(nome: str) -> str:
    nome_limpo = re.sub(r"[^A-Za-z0-9._-]", "_", nome or "ficheiro")
    return nome_limpo[-100:]  # nunca deixa o nome original inflacionar a chave indefinidamente


def gerar_chave(tenant_id, categoria: str, nome_original: str) -> str:
    """Chave única prefixada por tenant/categoria — o mesmo isolamento
    por tenant_id usado em toda a BD, aqui aplicado ao "caminho" do
    ficheiro no bucket/disco."""
    return f"{tenant_id}/{categoria}/{uuid.uuid4()}_{_sanitizar_nome(nome_original)}"


def _caminho_local(chave: str) -> Path:
    return UPLOAD_DIR / chave


async def guardar_ficheiro(chave: str, conteudo: bytes, content_type: str) -> None:
    if _s3_cliente is not None:
        await asyncio.to_thread(
            _s3_cliente.put_object, Bucket=S3_BUCKET, Key=chave, Body=conteudo, ContentType=content_type
        )
        return

    def _escrever():
        caminho = _caminho_local(chave)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)

    await asyncio.to_thread(_escrever)


async def obter_ficheiro(chave: str) -> bytes | None:
    """Devolve o conteúdo do ficheiro, ou None se não existir (nunca
    levanta por "não encontrado" — quem chamar decide se isso é 404)."""
    if _s3_cliente is not None:
        def _ler_s3():
            try:
                resposta = _s3_cliente.get_object(Bucket=S3_BUCKET, Key=chave)
                return resposta["Body"].read()
            except _s3_cliente.exceptions.NoSuchKey:
                return None
            except Exception:
                logger.exception("Falha ao ler '%s' do S3.", chave)
                return None
        return await asyncio.to_thread(_ler_s3)

    caminho = _caminho_local(chave)
    if not caminho.is_file():
        return None
    return await asyncio.to_thread(caminho.read_bytes)


async def apagar_ficheiro(chave: str) -> None:
    """Best-effort — uma falha a apagar o ficheiro antigo nunca deve
    impedir a operação principal (ex.: substituir o logótipo)."""
    if _s3_cliente is not None:
        def _apagar_s3():
            try:
                _s3_cliente.delete_object(Bucket=S3_BUCKET, Key=chave)
            except Exception:
                logger.exception("Falha ao apagar '%s' do S3.", chave)
        await asyncio.to_thread(_apagar_s3)
        return

    def _apagar_local():
        _caminho_local(chave).unlink(missing_ok=True)
    await asyncio.to_thread(_apagar_local)


_EXTENSOES_IMAGEM = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
}
# Documentos anexados (LeadDocumento, MatriculaDocumento, AlunoDocumento
# — ver docstrings respetivas) aceitam PDF além de imagem, e são vistos
# através deste mesmo obter_data_uri (ex.: onVerDocumento no front-end,
# que embute o resultado num <iframe src="...">). Sem esta entrada, um
# PDF caía no "senão" abaixo e saía rotulado como image/png — o iframe
# então tentava desenhar bytes de PDF como se fossem PNG e falhava
# silenciosamente (nunca apanhado antes por faltar um teste que
# efetivamente subisse e voltasse a ver um PDF, só PNGs de amostra).
_EXTENSOES_DOCUMENTO = {**_EXTENSOES_IMAGEM, ".pdf": "application/pdf"}


async def obter_data_uri(chave: str | None) -> str | None:
    """Lê um ficheiro do storage e devolve como data URI — usado tanto
    para imagens (cabeçalho dos PDFs gerados em documentos_pdf.py via
    obter_logo_data_uri abaixo, site_publico.py: logótipo e galeria de
    fotos) como para os documentos anexados que aceitam PDF além de
    imagem (LeadDocumento/MatriculaDocumento/AlunoDocumento). Nunca
    expõe uma URL direta do bucket a quem não tem sessão. None se a
    chave não existir ou a leitura falhar — nunca levanta, quem chamar
    decide o que fazer com "sem ficheiro"."""
    if not chave:
        return None
    conteudo = await obter_ficheiro(chave)
    if not conteudo:
        return None
    extensao = Path(chave).suffix.lower()
    content_type = _EXTENSOES_DOCUMENTO.get(extensao, "image/png")
    return f"data:{content_type};base64,{base64.b64encode(conteudo).decode()}"


async def obter_logo_data_uri(tenant) -> str | None:
    """Lê o logótipo da escola do storage e devolve como data URI —
    usado no cabeçalho dos PDFs gerados (documentos_pdf.py)."""
    chave = getattr(tenant, "logotipo_chave", None) if tenant else None
    return await obter_data_uri(chave)
