"""Página pública de apresentação de uma escola — ver
app/schemas/site_publico.py para a distinção entre a vista de gestão
(Configurações, GESTOR) e a vista pública (sem autenticação)."""
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.database.models import Tenant
from app.database.models_academico import Curso
from app.database.models_site_publico import SitePublicoFoto
from app.schemas.site_publico import CursoPublicoOut, SitePublicoConfigUpdate, SitePublicoOut

# Os 4 modelos visuais entre os quais a escola escolhe (ver
# gacademic/src/app/features/public/escola/templates/) — cada um com
# uma identidade própria (não é só cor: navegação, disposição do
# hero e dos cursos mudam de facto), pensados para "personalidades"
# de escola diferentes. Lista fechada de propósito: um modelo tem de
# ter componente Angular correspondente, não pode ser texto livre.
TEMPLATES_VALIDOS = {"classico", "moderno", "acolhedor", "editorial"}
_TEMPLATE_OMISSAO = "classico"

# Galeria pequena de propósito — isto é uma página de apresentação, não
# uma rede social; um limite baixo também mantém o payload da vista
# pública (fotos como data URI, ver storage.obter_data_uri) razoável.
_MAX_FOTOS = 8
_TIPOS_FOTO_ACEITES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_TAMANHO_MAXIMO_FOTO = 4 * 1024 * 1024  # 4 MB

# Só minúsculas, dígitos e hífen a separar palavras — nunca a começar
# ou acabar em hífen, nunca hífen repetido. Isto entra num URL global
# (/escola/<slug>), por isso é mais restrito que um nome de utilizador
# comum: precisa de ficar legível e sem ambiguidade quando escrito à
# mão num flyer.
_SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _normalizar_slug(slug: str | None) -> str | None:
    slug = (slug or "").strip().lower()
    if not slug:
        return None
    if len(slug) < 3 or len(slug) > 80 or not _SLUG_REGEX.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Endereço inválido. Use só letras minúsculas, números e hífen (ex.: colegio-do-futuro), entre 3 e 80 carateres.",
        )
    return slug


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
        "slug": tenant.site_publico_slug,
        "template": tenant.site_publico_template,
        "missao": tenant.site_publico_missao,
        "metodologia": tenant.site_publico_metodologia,
        "facebook": tenant.site_publico_facebook,
        "instagram": tenant.site_publico_instagram,
        "whatsapp": tenant.site_publico_whatsapp,
        "fotos": [{"id": f.id, "url": url} for f, url in zip(fotos, urls) if url],
    }


async def atualizar_config(db: AsyncSession, tenant_id, dados: SitePublicoConfigUpdate) -> dict:
    tenant = await _obter_tenant(db, tenant_id)
    novo_slug = _normalizar_slug(dados.slug)
    if novo_slug and novo_slug != tenant.site_publico_slug:
        em_uso = (await db.execute(
            select(Tenant.id).where(Tenant.site_publico_slug == novo_slug, Tenant.id != tenant_id)
        )).scalars().first()
        if em_uso:
            raise HTTPException(status_code=400, detail="Este endereço já está a ser usado por outra escola. Escolha outro.")

    if dados.template not in TEMPLATES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Modelo inválido. Escolha um de: {', '.join(sorted(TEMPLATES_VALIDOS))}.")

    tenant.site_publico_ativo = dados.ativo
    tenant.site_publico_slug = novo_slug
    tenant.site_publico_template = dados.template
    tenant.site_publico_missao = (dados.missao or "").strip() or None
    tenant.site_publico_metodologia = (dados.metodologia or "").strip() or None
    tenant.site_publico_facebook = (dados.facebook or "").strip() or None
    tenant.site_publico_instagram = (dados.instagram or "").strip() or None
    tenant.site_publico_whatsapp = re.sub(r"\D", "", dados.whatsapp or "") or None
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

async def obter_site_publico(db: AsyncSession, identificador: str) -> SitePublicoOut:
    # Aceita tanto o slug legível (/escola/colegio-do-futuro, o caminho a
    # divulgar) como o uuid do tenant (/escola/<uuid>, para não quebrar
    # o que já foi partilhado antes de a escola escolher um slug).
    try:
        filtro = Tenant.id == uuid.UUID(identificador)
    except ValueError:
        filtro = Tenant.site_publico_slug == identificador.strip().lower()

    tenant = (await db.execute(select(Tenant).where(filtro))).scalars().first()
    if not tenant or not tenant.site_publico_ativo:
        # Mesma mensagem genérica para "não existe" e para "existe mas
        # está desativada" — não é ao visitante que interessa saber
        # qual dos dois casos é.
        raise HTTPException(status_code=404, detail="Esta página não está disponível.")

    cursos_rows = (await db.execute(
        select(Curso).where(Curso.tenant_id == tenant.id, Curso.site_publico_visivel.is_(True)).order_by(Curso.nome)
    )).scalars().all()
    cursos = [CursoPublicoOut(id=c.id, nome=c.nome, descricao=c.site_publico_descricao) for c in cursos_rows]
    fotos_rows = await _listar_fotos(db, tenant.id)
    # NOTA: "await ... for f in fotos_rows" dentro de uma expressão
    # geradora (parênteses) seria um async generator — precisaria de
    # "async for" para consumir. Numa list comprehension (colchetes)
    # dentro de uma função async, o "await" por iteração É avaliado de
    # forma síncrona/sequencial, sem essa armadilha.
    fotos_urls = [url for url in [await storage.obter_data_uri(f.chave_storage) for f in fotos_rows] if url]
    logotipo = await storage.obter_data_uri(tenant.logotipo_chave)

    return SitePublicoOut(
        tenant_id=tenant.id, nome_fantasia=tenant.nome_fantasia,
        template=tenant.site_publico_template if tenant.site_publico_template in TEMPLATES_VALIDOS else _TEMPLATE_OMISSAO,
        logotipo=logotipo,
        missao=tenant.site_publico_missao, metodologia=tenant.site_publico_metodologia,
        telefone_contacto=tenant.telefone_contacto, email_contacto=tenant.email_contacto,
        morada=tenant.morada, cidade=tenant.cidade,
        facebook=tenant.site_publico_facebook, instagram=tenant.site_publico_instagram,
        whatsapp=tenant.site_publico_whatsapp,
        cursos=cursos, fotos=fotos_urls,
    )
