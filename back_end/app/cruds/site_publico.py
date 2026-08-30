"""Página pública de apresentação de uma escola — ver
app/schemas/site_publico.py para a distinção entre a vista de gestão
(Configurações, GESTOR) e a vista pública (sem autenticação)."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.database.models import Tenant
from app.database.models_academico import Curso
from app.database.models_site_publico import SitePublicoFoto
from app.schemas.site_publico import SitePublicoConfigUpdate, SitePublicoOut

# Galeria pequena de propósito — isto é uma página de apresentação, não
# uma rede social; um limite baixo também mantém o payload da vista
# pública (fotos como data URI, ver storage.obter_data_uri) razoável.
_MAX_FOTOS = 8
_TIPOS_FOTO_ACEITES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_TAMANHO_MAXIMO_FOTO = 4 * 1024 * 1024  # 4 MB


async def _obter_tenant(db: AsyncSession, tenant_id) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    return tenant


async def _listar_fotos(db: AsyncSession, tenant_id) -> list[SitePublicoFoto]:
    return (await db.execute(
        select(SitePublicoFoto).where(SitePublicoFoto.tenant_id == tenant_id).order_by(SitePublicoFoto.ordem, SitePublicoFoto.data_criacao)
    )).scalars().all()


async def obter_config(db: AsyncSession, tenant_id) -> dict:
    tenant = await _obter_tenant(db, tenant_id)
    fotos = await _listar_fotos(db, tenant_id)
    urls = [await storage.obter_data_uri(f.chave_storage) for f in fotos]
    return {
        "ativo": tenant.site_publico_ativo,
        "missao": tenant.site_publico_missao,
        "metodologia": tenant.site_publico_metodologia,
        "fotos": [{"id": f.id, "url": url} for f, url in zip(fotos, urls) if url],
    }


async def atualizar_config(db: AsyncSession, tenant_id, dados: SitePublicoConfigUpdate) -> dict:
    tenant = await _obter_tenant(db, tenant_id)
    tenant.site_publico_ativo = dados.ativo
    tenant.site_publico_missao = (dados.missao or "").strip() or None
    tenant.site_publico_metodologia = (dados.metodologia or "").strip() or None
    await db.commit()
    return await obter_config(db, tenant_id)


async def adicionar_foto(db: AsyncSession, tenant_id, nome_original: str, content_type: str, conteudo: bytes) -> dict:
    if content_type not in _TIPOS_FOTO_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato de imagem não aceite ({content_type}). Use PNG, JPEG, GIF ou WebP.")
    if len(conteudo) > _TAMANHO_MAXIMO_FOTO:
        raise HTTPException(status_code=400, detail="Cada foto não pode passar de 4 MB.")

    await _obter_tenant(db, tenant_id)
    total_atual = len((await _listar_fotos(db, tenant_id)))
    if total_atual >= _MAX_FOTOS:
        raise HTTPException(status_code=400, detail=f"Já tem o máximo de {_MAX_FOTOS} fotos — apague uma antes de adicionar outra.")

    chave = storage.gerar_chave(tenant_id, "site-publico", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    db.add(SitePublicoFoto(tenant_id=tenant_id, chave_storage=chave, ordem=total_atual))
    await db.commit()
    return await obter_config(db, tenant_id)


async def remover_foto(db: AsyncSession, tenant_id, foto_id: uuid.UUID) -> dict:
    foto = (await db.execute(
        select(SitePublicoFoto).where(SitePublicoFoto.id == foto_id, SitePublicoFoto.tenant_id == tenant_id)
    )).scalars().first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    chave = foto.chave_storage
    await db.delete(foto)
    await db.commit()
    await storage.apagar_ficheiro(chave)
    return await obter_config(db, tenant_id)


# ==========================================
# Vista pública (sem autenticação)
# ==========================================

async def obter_site_publico(db: AsyncSession, tenant_id) -> SitePublicoOut:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant or not tenant.site_publico_ativo:
        # Mesma mensagem genérica para "não existe" e para "existe mas
        # está desativada" — não é ao visitante que interessa saber
        # qual dos dois casos é.
        raise HTTPException(status_code=404, detail="Esta página não está disponível.")

    cursos = (await db.execute(
        select(Curso.nome).where(Curso.tenant_id == tenant_id).order_by(Curso.nome)
    )).scalars().all()
    fotos_rows = await _listar_fotos(db, tenant_id)
    # NOTA: "await ... for f in fotos_rows" dentro de uma expressão
    # geradora (parênteses) seria um async generator — precisaria de
    # "async for" para consumir. Numa list comprehension (colchetes)
    # dentro de uma função async, o "await" por iteração É avaliado de
    # forma síncrona/sequencial, sem essa armadilha.
    fotos_urls = [url for url in [await storage.obter_data_uri(f.chave_storage) for f in fotos_rows] if url]
    logotipo = await storage.obter_data_uri(tenant.logotipo_chave)

    return SitePublicoOut(
        tenant_id=tenant.id, nome_fantasia=tenant.nome_fantasia, logotipo=logotipo,
        missao=tenant.site_publico_missao, metodologia=tenant.site_publico_metodologia,
        telefone_contacto=tenant.telefone_contacto, email_contacto=tenant.email_contacto,
        morada=tenant.morada, cidade=tenant.cidade,
        cursos=list(cursos), fotos=fotos_urls,
    )
