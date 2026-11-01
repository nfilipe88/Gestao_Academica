"""Perfis da escola (bloco D2) — o Gestor cria perfis a partir da
Secretaria ou do Professor (ex.: "Tesouraria") e escolhe, módulo a módulo,
o que ficam a poder fazer. Nunca acima do que o perfil base pode na escola
(mapa base E restrições da escola) — ver app/core/mapa_permissoes.py.

Quem tem um destes perfis continua com perfil_acesso igual ao base: o
código trata-o como Secretaria/Professor (incluindo que dados vê); o mapa
tira-lhe o resto.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import mapa_permissoes, nomes_perfil
from app.cruds.permissoes import _teto
from app.database.models import Usuario
from app.database.models_permissoes import (
    PERFIS_BASE_PERSONALIZAVEIS, PerfilPersonalizado, PerfilPersonalizadoPermissao, PermissaoModulo, PermissaoModuloEscola,
)
from app.schemas.permissoes import PermissaoModuloUpdate

OPERACOES = mapa_permissoes.OPERACOES


async def _limite_da_escola(db: AsyncSession, tenant_id, perfil_base: str) -> list[dict]:
    """Para cada módulo do mapa, o que o perfil base pode NESTA escola —
    o teto de um perfil da escola."""
    coluna = PERFIS_BASE_PERSONALIZAVEIS[perfil_base]
    linhas = (await db.execute(
        select(PermissaoModulo).where(PermissaoModulo.perfil == coluna).order_by(PermissaoModulo.ordem)
    )).scalars().all()
    restricoes = {
        r.modulo: r for r in (await db.execute(
            select(PermissaoModuloEscola).where(
                PermissaoModuloEscola.tenant_id == tenant_id, PermissaoModuloEscola.perfil == coluna)
        )).scalars().all()
    }
    teto = _teto()
    limites = []
    for linha in linhas:
        restricao = restricoes.get(linha.modulo)
        limites.append({
            "modulo": linha.modulo, "ordem": linha.ordem,
            # Sem rotas associadas (ex.: Visão Geral) — não há nada a restringir.
            "informativo": (linha.modulo, coluna) not in teto,
            **{op: getattr(linha, op) and (getattr(restricao, op) if restricao else True) for op in OPERACOES},
        })
    return limites


async def _vista(db: AsyncSession, perfil: PerfilPersonalizado) -> dict:
    limites = await _limite_da_escola(db, perfil.tenant_id, perfil.perfil_base)
    proprias = {
        l.modulo: l for l in (await db.execute(
            select(PerfilPersonalizadoPermissao).where(PerfilPersonalizadoPermissao.perfil_personalizado_id == perfil.id)
        )).scalars().all()
    }
    n_utilizadores = (await db.execute(
        select(func.count()).select_from(Usuario).where(Usuario.perfil_personalizado_id == perfil.id)
    )).scalar_one()
    permissoes = []
    for limite in limites:
        propria = proprias.get(limite["modulo"])
        permissoes.append({
            "modulo": limite["modulo"], "ordem": limite["ordem"], "informativo": limite["informativo"],
            # O que vale de facto: o do perfil E o que a escola deixa ao base.
            # Linhas só informativas não decidem nada — mostram o do perfil base.
            **{op: limite[op] if limite["informativo"] else bool(propria and getattr(propria, op)) and limite[op]
               for op in OPERACOES},
            **{f"limite_{op}": limite[op] for op in OPERACOES},
        })
    return {
        "id": perfil.id, "nome": perfil.nome, "perfil_base": perfil.perfil_base,
        "n_utilizadores": n_utilizadores, "permissoes": permissoes,
    }


async def _obter(db: AsyncSession, tenant_id, perfil_id: uuid.UUID) -> PerfilPersonalizado:
    perfil = (await db.execute(
        select(PerfilPersonalizado).where(PerfilPersonalizado.id == perfil_id, PerfilPersonalizado.tenant_id == tenant_id)
    )).scalars().first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil da escola não encontrado.")
    return perfil


async def _validar_nome(db: AsyncSession, tenant_id, nome: str, excluir_id: uuid.UUID | None = None) -> str:
    nome = " ".join(nome.split())
    if len(nome) < 2:
        raise HTTPException(status_code=400, detail="O nome tem de ter pelo menos 2 caracteres.")
    # Um nome igual ao de um perfil da plataforma tornava as listas ambíguas.
    if nome.lower() in {n.lower() for n in (await nomes_perfil.obter_nomes()).values()}:
        raise HTTPException(status_code=400, detail=f'"{nome}" já é o nome de um perfil da plataforma — escolha outro.')
    consulta = select(PerfilPersonalizado).where(
        PerfilPersonalizado.tenant_id == tenant_id, func.lower(PerfilPersonalizado.nome) == nome.lower())
    if excluir_id is not None:
        consulta = consulta.where(PerfilPersonalizado.id != excluir_id)
    if (await db.execute(consulta)).scalars().first():
        raise HTTPException(status_code=400, detail=f'A escola já tem um perfil chamado "{nome}".')
    return nome


async def listar(db: AsyncSession, tenant_id) -> list[dict]:
    perfis = (await db.execute(
        select(PerfilPersonalizado).where(PerfilPersonalizado.tenant_id == tenant_id).order_by(PerfilPersonalizado.nome)
    )).scalars().all()
    return [await _vista(db, p) for p in perfis]


async def criar(db: AsyncSession, tenant_id, nome: str, perfil_base: str) -> dict:
    """Começa igual ao perfil base na escola — o Gestor depois desmarca."""
    if perfil_base not in PERFIS_BASE_PERSONALIZAVEIS:
        raise HTTPException(status_code=400, detail="Um perfil da escola só pode partir da Secretaria ou do Professor.")
    nome = await _validar_nome(db, tenant_id, nome)
    perfil = PerfilPersonalizado(tenant_id=tenant_id, nome=nome, perfil_base=perfil_base)
    db.add(perfil)
    await db.flush()
    for limite in await _limite_da_escola(db, tenant_id, perfil_base):
        if limite["informativo"]:
            continue
        db.add(PerfilPersonalizadoPermissao(
            tenant_id=tenant_id, perfil_personalizado_id=perfil.id, modulo=limite["modulo"],
            **{op: limite[op] for op in OPERACOES},
        ))
    await db.commit()
    await db.refresh(perfil)
    return await _vista(db, perfil)


async def renomear(db: AsyncSession, tenant_id, perfil_id: uuid.UUID, nome: str) -> dict:
    perfil = await _obter(db, tenant_id, perfil_id)
    perfil.nome = await _validar_nome(db, tenant_id, nome, excluir_id=perfil.id)
    await db.commit()
    await db.refresh(perfil)
    mapa_permissoes.invalidar_cache()
    return await _vista(db, perfil)


async def atualizar_modulo(db: AsyncSession, tenant_id, perfil_id: uuid.UUID, modulo: str, dados: PermissaoModuloUpdate) -> dict:
    perfil = await _obter(db, tenant_id, perfil_id)
    limite = next((l for l in await _limite_da_escola(db, tenant_id, perfil.perfil_base) if l["modulo"] == modulo), None)
    if limite is None:
        raise HTTPException(status_code=404, detail="Módulo não encontrado no Mapa de Permissões.")
    if limite["informativo"]:
        raise HTTPException(status_code=400, detail=f"{modulo} é só informativo — não há nada a restringir.")
    for op in OPERACOES:
        if getattr(dados, op) and not limite[op]:
            nome_base = await nomes_perfil.nome(perfil.perfil_base)
            raise HTTPException(
                status_code=400,
                detail=f"Na escola, {nome_base} não pode {mapa_permissoes.NOME_OPERACAO[op]} em {modulo} — "
                       f"um perfil da escola só pode ter menos do que o perfil base.",
            )
    linha = (await db.execute(
        select(PerfilPersonalizadoPermissao).where(
            PerfilPersonalizadoPermissao.perfil_personalizado_id == perfil.id, PerfilPersonalizadoPermissao.modulo == modulo)
    )).scalars().first()
    if not linha:
        linha = PerfilPersonalizadoPermissao(tenant_id=tenant_id, perfil_personalizado_id=perfil.id, modulo=modulo)
        db.add(linha)
    for op in OPERACOES:
        setattr(linha, op, getattr(dados, op))
    await db.commit()
    mapa_permissoes.invalidar_cache()
    return await _vista(db, perfil)


async def apagar(db: AsyncSession, tenant_id, perfil_id: uuid.UUID) -> None:
    """Quem o tinha volta ao perfil base (usuario.perfil_personalizado_id ON DELETE SET NULL)."""
    perfil = await _obter(db, tenant_id, perfil_id)
    await db.delete(perfil)
    await db.commit()
    mapa_permissoes.invalidar_cache()
