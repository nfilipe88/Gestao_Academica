"""Administração de QUEM assina cada tipo de documento formal (Gestor) —
ver app/schemas/assinantes_documento.py e app/database/models.py::
AssinanteDocumento. A leitura usada na geração real do PDF vive à parte,
em app/core/assinaturas.py::obter_assinantes_documento (sem RBAC, é
interna ao processo de emissão)."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AssinanteDocumento, Usuario
from app.schemas.assinantes_documento import AssinanteDocumentoCreate, AssinanteDocumentoUpdate

# Só faz sentido de negócio staff assinar documentos — um ALUNO/RESPONSAVEL
# nunca devia poder ser designado assinante de um Certificado.
_PERFIS_ELEGIVEIS = ("GESTOR", "SECRETARIA", "PROFESSOR")


def _serializar(assinante: AssinanteDocumento, nome: str) -> dict:
    return {
        "id": assinante.id, "tipo_documento": assinante.tipo_documento,
        "usuario_id": assinante.usuario_id, "nome_usuario": nome,
        "cargo": assinante.cargo, "ordem": assinante.ordem,
    }


async def listar_assinantes(db: AsyncSession, tenant_id) -> list[dict]:
    """Todos os assinantes configurados, de todos os tipos — o frontend
    agrupa por tipo_documento. Ordenado por tipo e depois por ordem, para
    a listagem já sair coerente com a ordem usada nos PDFs."""
    linhas = (await db.execute(
        select(AssinanteDocumento, Usuario.nome_completo)
        .join(Usuario, Usuario.id == AssinanteDocumento.usuario_id)
        .where(AssinanteDocumento.tenant_id == tenant_id)
        .order_by(AssinanteDocumento.tipo_documento, AssinanteDocumento.ordem)
    )).all()
    return [_serializar(a, nome) for a, nome in linhas]


async def adicionar_assinante(db: AsyncSession, tenant_id, dados: AssinanteDocumentoCreate) -> dict:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == dados.usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado na sua instituição.")
    if usuario.perfil_acesso not in _PERFIS_ELEGIVEIS:
        raise HTTPException(status_code=400, detail="Só membros do staff (Gestor, Secretaria, Professor) podem ser assinantes.")

    existente = (await db.execute(
        select(AssinanteDocumento).where(
            AssinanteDocumento.tenant_id == tenant_id, AssinanteDocumento.tipo_documento == dados.tipo_documento,
            AssinanteDocumento.usuario_id == dados.usuario_id,
        )
    )).scalars().first()
    if existente:
        raise HTTPException(status_code=400, detail=f'"{usuario.nome_completo}" já está atribuído a este tipo de documento.')

    novo = AssinanteDocumento(
        tenant_id=tenant_id, tipo_documento=dados.tipo_documento, usuario_id=dados.usuario_id,
        cargo=dados.cargo.strip(), ordem=dados.ordem,
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return _serializar(novo, usuario.nome_completo)


async def atualizar_assinante(db: AsyncSession, tenant_id, assinante_id: uuid.UUID, dados: AssinanteDocumentoUpdate) -> dict:
    assinante = (await db.execute(
        select(AssinanteDocumento).where(AssinanteDocumento.id == assinante_id, AssinanteDocumento.tenant_id == tenant_id)
    )).scalars().first()
    if not assinante:
        raise HTTPException(status_code=404, detail="Assinante não encontrado.")
    assinante.cargo = dados.cargo.strip()
    assinante.ordem = dados.ordem
    await db.commit()
    await db.refresh(assinante)
    usuario = (await db.execute(select(Usuario).where(Usuario.id == assinante.usuario_id))).scalars().first()
    return _serializar(assinante, usuario.nome_completo if usuario else "")


async def remover_assinante(db: AsyncSession, tenant_id, assinante_id: uuid.UUID) -> None:
    assinante = (await db.execute(
        select(AssinanteDocumento).where(AssinanteDocumento.id == assinante_id, AssinanteDocumento.tenant_id == tenant_id)
    )).scalars().first()
    if not assinante:
        raise HTTPException(status_code=404, detail="Assinante não encontrado.")
    await db.delete(assinante)
    await db.commit()
