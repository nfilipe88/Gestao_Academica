"""Área de Eventos da escola — ver app/schemas/eventos.py e
app/database/models_eventos.py para a distinção face ao Site Público."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.database.models import Tenant
from app.database.models_eventos import Evento, EventoFoto
from app.schemas.eventos import EventoCreate, EventoUpdate
# Mesmas constantes de validação de imagem do Site Público — reutilizadas
# para não haver duas fontes de verdade sobre tipos/tamanho aceites.
from app.cruds.site_publico import _TAMANHO_MAXIMO_FOTO, _TIPOS_FOTO_ACEITES


async def _obter_tenant(db: AsyncSession, tenant_id) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    return tenant


async def _obter_evento(db: AsyncSession, tenant_id, evento_id: uuid.UUID) -> Evento:
    evento = (await db.execute(
        select(Evento).where(Evento.id == evento_id, Evento.tenant_id == tenant_id)
    )).scalars().first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado na sua instituição.")
    return evento


async def _listar_fotos(db: AsyncSession, tenant_id, evento_id: uuid.UUID) -> list[EventoFoto]:
    return (await db.execute(
        select(EventoFoto).where(EventoFoto.tenant_id == tenant_id, EventoFoto.evento_id == evento_id)
        .order_by(EventoFoto.ordem, EventoFoto.data_criacao)
    )).scalars().all()


async def _serializar(db: AsyncSession, evento: Evento) -> dict:
    fotos = await _listar_fotos(db, evento.tenant_id, evento.id)
    urls = [await storage.obter_data_uri(f.chave_storage) for f in fotos]
    return {
        "id": evento.id,
        "titulo": evento.titulo,
        "data": evento.data,
        "descricao": evento.descricao,
        "publicado": evento.publicado,
        "fotos": [{"id": f.id, "url": url} for f, url in zip(fotos, urls) if url],
    }


async def criar_evento(db: AsyncSession, tenant_id, dados: EventoCreate) -> dict:
    await _obter_tenant(db, tenant_id)
    novo = Evento(
        tenant_id=tenant_id, titulo=dados.titulo, data=dados.data,
        descricao=dados.descricao, publicado=dados.publicado,
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return await _serializar(db, novo)


async def listar_eventos(db: AsyncSession, tenant_id) -> list[dict]:
    """Vista de gestão (GESTOR) — todos os eventos, publicados ou não."""
    eventos = (await db.execute(
        select(Evento).where(Evento.tenant_id == tenant_id).order_by(Evento.data.desc())
    )).scalars().all()
    return [await _serializar(db, e) for e in eventos]


async def atualizar_evento(db: AsyncSession, tenant_id, evento_id: uuid.UUID, dados: EventoUpdate) -> dict:
    evento = await _obter_evento(db, tenant_id, evento_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(evento, campo, valor)
    await db.commit()
    await db.refresh(evento)
    return await _serializar(db, evento)


async def remover_evento(db: AsyncSession, tenant_id, evento_id: uuid.UUID) -> None:
    evento = await _obter_evento(db, tenant_id, evento_id)
    fotos = await _listar_fotos(db, tenant_id, evento_id)
    chaves = [f.chave_storage for f in fotos]
    await db.delete(evento)  # cascade apaga as linhas de EventoFoto
    await db.commit()
    for chave in chaves:
        await storage.apagar_ficheiro(chave)


async def adicionar_foto_evento(db: AsyncSession, tenant_id, evento_id: uuid.UUID, nome_original: str, content_type: str, conteudo: bytes) -> dict:
    """Ao contrário de site_publico.py::adicionar_foto, NÃO há limite de
    contagem aqui — de propósito: um evento pode ter tantas fotos
    quantas fizerem sentido para contar a história desse dia, sem o
    limite de 8 pensado para a galeria genérica da página."""
    if content_type not in _TIPOS_FOTO_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato de imagem não aceite ({content_type}). Use PNG, JPEG, GIF ou WebP.")
    if len(conteudo) > _TAMANHO_MAXIMO_FOTO:
        raise HTTPException(status_code=400, detail="Cada foto não pode passar de 4 MB.")

    await _obter_evento(db, tenant_id, evento_id)
    total_atual = len(await _listar_fotos(db, tenant_id, evento_id))

    chave = storage.gerar_chave(tenant_id, "eventos", nome_original)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    db.add(EventoFoto(tenant_id=tenant_id, evento_id=evento_id, chave_storage=chave, ordem=total_atual))
    await db.commit()
    evento = await _obter_evento(db, tenant_id, evento_id)
    return await _serializar(db, evento)


async def remover_foto_evento(db: AsyncSession, tenant_id, evento_id: uuid.UUID, foto_id: uuid.UUID) -> dict:
    foto = (await db.execute(
        select(EventoFoto).where(EventoFoto.id == foto_id, EventoFoto.tenant_id == tenant_id, EventoFoto.evento_id == evento_id)
    )).scalars().first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    chave = foto.chave_storage
    await db.delete(foto)
    await db.commit()
    await storage.apagar_ficheiro(chave)
    evento = await _obter_evento(db, tenant_id, evento_id)
    return await _serializar(db, evento)


# ==========================================
# Vista pública (sem autenticação, embutida em SitePublicoOut)
# ==========================================
async def listar_eventos_publicos(db: AsyncSession, tenant_id) -> list[dict]:
    eventos = (await db.execute(
        select(Evento).where(Evento.tenant_id == tenant_id, Evento.publicado.is_(True)).order_by(Evento.data.desc())
    )).scalars().all()
    resultado = []
    for evento in eventos:
        fotos = await _listar_fotos(db, tenant_id, evento.id)
        urls = [url for url in [await storage.obter_data_uri(f.chave_storage) for f in fotos] if url]
        resultado.append({
            "id": evento.id, "titulo": evento.titulo, "data": evento.data,
            "descricao": evento.descricao, "fotos": urls,
        })
    return resultado
