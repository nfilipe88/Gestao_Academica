"""
Assinatura digital para documentos PDF formais (Certificado, Declaração,
Histórico Escolar, Boletim, Recibo — os tipos que passam pelo bloco
`.assinaturas` de documentos_pdf.py::_ENVELOPE), substituindo a
assinatura física.

Dois níveis distintos (ver app/database/models.py):
- AssinaturaUsuario: a imagem/traço PESSOAL de cada membro do staff
  (self-service, ver app/cruds/perfil.py) — a FONTE da imagem.
- AssinanteDocumento: decisão ADMINISTRATIVA da escola sobre QUEM assina
  cada TIPO de documento (ex.: Certificado = Diretor Geral + Diretor
  Pedagógico; Boletim = só o Pedagógico) — a CAMADA DE ATRIBUIÇÃO, gerida
  em Configurações > Assinantes de Documentos (ver
  app/cruds/assinantes_documento.py para o CRUD de administração).

obter_assinantes_documento nunca depende de "quem gerou o PDF" — só de
tenant_id + tipo_documento. Os 3 call-sites (cruds/documentos.py::
gerar_pdf_solicitacao, cruds/financeiro.py::gerar_pdf_recibo,
cruds/transferencias.py — histórico automático, sempre do tenant de
ORIGEM) chamam todos a mesma função, sem precisar de um `utilizador`
completo disponível.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.database.models import AssinanteDocumento, AssinaturaUsuario, Usuario


async def obter_assinantes_documento(db: AsyncSession, tenant_id, tipo_documento: str) -> list[dict]:
    """[{"nome": str, "cargo": str, "data_uri": str | None}, ...] ordenado
    por `ordem` — lista vazia se a escola não atribuiu ninguém a este tipo
    (o bloco de assinatura do envelope sai só com uma linha em branco,
    sem imagem nem texto nenhum). `data_uri` vem da assinatura pessoal
    ATIVA do usuario_id designado, se existir — None quando essa pessoa
    ainda não configurou a sua em "O Meu Perfil" (mostra só a linha com o
    nome/cargo, sem imagem)."""
    linhas = (await db.execute(
        select(AssinanteDocumento, Usuario.nome_completo)
        .join(Usuario, Usuario.id == AssinanteDocumento.usuario_id)
        .where(AssinanteDocumento.tenant_id == tenant_id, AssinanteDocumento.tipo_documento == tipo_documento)
        .order_by(AssinanteDocumento.ordem)
    )).all()

    resultado = []
    for assinante, nome in linhas:
        chave = (await db.execute(
            select(AssinaturaUsuario.chave_storage).where(
                AssinaturaUsuario.tenant_id == tenant_id,
                AssinaturaUsuario.usuario_id == assinante.usuario_id,
                AssinaturaUsuario.ativa.is_(True),
            )
        )).scalar_one_or_none()
        data_uri = await storage.obter_data_uri(chave) if chave else None
        resultado.append({"nome": nome, "cargo": assinante.cargo, "data_uri": data_uri})
    return resultado
