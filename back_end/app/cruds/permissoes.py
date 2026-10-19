import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import mapa_permissoes, nomes_perfil
from app.database.models_permissoes import PerfilNome, PermissaoModulo, PermissaoModuloEscola
from app.schemas.permissoes import PermissaoModuloUpdate

_teto_cache: dict | None = None


def _teto() -> dict:
    """Teto do código, calculado uma vez a partir das rotas da app."""
    global _teto_cache
    if _teto_cache is None:
        from main import app
        _teto_cache = mapa_permissoes.teto_do_codigo(app)
    return _teto_cache


def _vista(linha: PermissaoModulo, restricao: PermissaoModuloEscola | None, vista_escola: bool) -> dict:
    teto = _teto().get((linha.modulo, linha.perfil))
    dados = {
        "id": linha.id, "ordem": linha.ordem, "modulo": linha.modulo, "perfil": linha.perfil,
        **{op: getattr(linha, op) for op in mapa_permissoes.OPERACOES},
        **{f"codigo_{op}": (teto[op] if teto else True) for op in mapa_permissoes.OPERACOES},
        "informativo": teto is None,
        "protegidas": [op for op in mapa_permissoes.OPERACOES if (linha.modulo, linha.perfil, op) in mapa_permissoes.PROTEGIDOS],
    }
    if vista_escola:
        for op in mapa_permissoes.OPERACOES:
            dados[f"escola_{op}"] = getattr(linha, op) and (getattr(restricao, op) if restricao else True)
    return dados


async def listar_permissoes(db: AsyncSession, tenant_id=None) -> list[dict]:
    """Mapa completo. Com tenant_id (vista do Gestor), acrescenta o que vale
    nessa escola (mapa base E restrições da escola)."""
    linhas = (await db.execute(
        select(PermissaoModulo).order_by(PermissaoModulo.ordem, PermissaoModulo.perfil)
    )).scalars().all()
    restricoes = {}
    if tenant_id is not None:
        restricoes = {
            (r.modulo, r.perfil): r for r in (await db.execute(
                select(PermissaoModuloEscola).where(PermissaoModuloEscola.tenant_id == tenant_id)
            )).scalars().all()
        }
    return [_vista(l, restricoes.get((l.modulo, l.perfil)), tenant_id is not None) for l in linhas]


async def _obter_linha(db: AsyncSession, permissao_id: uuid.UUID) -> PermissaoModulo:
    linha = (await db.execute(select(PermissaoModulo).where(PermissaoModulo.id == permissao_id))).scalars().first()
    if not linha:
        raise HTTPException(status_code=404, detail="Célula do mapa de permissões não encontrada.")
    if linha.perfil == "super_admin":
        raise HTTPException(status_code=400, detail="O Super Admin não é restringido pelo mapa (nunca se pode trancar fora).")
    return linha


async def atualizar_permissao(db: AsyncSession, permissao_id: uuid.UUID, dados: PermissaoModuloUpdate) -> dict:
    """Mapa base (Super Admin): vale para todas as escolas. Nunca acima do código."""
    linha = await _obter_linha(db, permissao_id)
    teto = _teto().get((linha.modulo, linha.perfil))
    for op in mapa_permissoes.OPERACOES:
        pedido = getattr(dados, op)
        if pedido and teto and not teto[op]:
            raise HTTPException(
                status_code=400,
                detail=f"O código não deixa este perfil {mapa_permissoes.NOME_OPERACAO[op]} em {linha.modulo} — o mapa só pode restringir.",
            )
        if not pedido and (linha.modulo, linha.perfil, op) in mapa_permissoes.PROTEGIDOS:
            raise HTTPException(status_code=400, detail=f"Esta permissão é protegida: o Gestor nunca pode perder o acesso a {linha.modulo}.")
    for op in mapa_permissoes.OPERACOES:
        setattr(linha, op, getattr(dados, op))
    await db.commit()
    await db.refresh(linha)
    mapa_permissoes.invalidar_cache()
    return _vista(linha, None, False)


async def restringir_na_escola(db: AsyncSession, tenant_id, permissao_id: uuid.UUID, dados: PermissaoModuloUpdate) -> dict:
    """Mapa da escola (Gestor): só pode tirar ao que o mapa base dá, e só na
    própria escola. Igual ao base = sem restrição (a linha desaparece)."""
    linha = await _obter_linha(db, permissao_id)
    for op in mapa_permissoes.OPERACOES:
        pedido = getattr(dados, op)
        if pedido and not getattr(linha, op):
            raise HTTPException(
                status_code=400,
                detail=f"O mapa base da plataforma não deixa este perfil {mapa_permissoes.NOME_OPERACAO[op]} em {linha.modulo} — a escola só pode restringir.",
            )
        if not pedido and (linha.modulo, linha.perfil, op) in mapa_permissoes.PROTEGIDOS:
            raise HTTPException(status_code=400, detail=f"Esta permissão é protegida: o Gestor nunca pode perder o acesso a {linha.modulo}.")
    restricao = (await db.execute(
        select(PermissaoModuloEscola).where(
            PermissaoModuloEscola.tenant_id == tenant_id, PermissaoModuloEscola.modulo == linha.modulo,
            PermissaoModuloEscola.perfil == linha.perfil,
        )
    )).scalars().first()
    if all(getattr(dados, op) == getattr(linha, op) for op in mapa_permissoes.OPERACOES):
        if restricao:
            await db.delete(restricao)
        restricao = None
    else:
        if not restricao:
            restricao = PermissaoModuloEscola(tenant_id=tenant_id, modulo=linha.modulo, perfil=linha.perfil)
            db.add(restricao)
        for op in mapa_permissoes.OPERACOES:
            setattr(restricao, op, getattr(dados, op))
    await db.commit()
    mapa_permissoes.invalidar_cache()
    return _vista(linha, restricao, True)


# ==========================================
# NOMES DOS PERFIS (ver models_permissoes.py::PerfilNome)
# ==========================================
async def listar_nomes_perfis(db: AsyncSession) -> list[PerfilNome]:
    return list((await db.execute(select(PerfilNome).order_by(PerfilNome.ordem))).scalars().all())


async def renomear_perfil(db: AsyncSession, codigo: str, nome: str) -> PerfilNome:
    perfil = await db.get(PerfilNome, codigo)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")
    nome = " ".join(nome.split())
    if len(nome) < 2:
        raise HTTPException(status_code=400, detail="O nome tem de ter pelo menos 2 caracteres.")
    repetido = (await db.execute(
        select(PerfilNome).where(func.lower(PerfilNome.nome) == nome.lower(), PerfilNome.codigo != codigo)
    )).scalars().first()
    if repetido:
        # Dois perfis com o mesmo nome tornavam impossível saber quem é quem nas listas.
        raise HTTPException(status_code=400, detail=f'O nome "{nome}" já é usado pelo perfil {repetido.codigo}.')
    perfil.nome = nome
    await db.commit()
    await db.refresh(perfil)
    nomes_perfil.invalidar()
    return perfil
