"""
Nomes mostrados dos perfis (ex.: GESTOR → "Diretor Geral"), editáveis pelo
Super Admin — ver models_permissoes.py::PerfilNome.

Cache em memória de 60 s: os nomes entram em mensagens de erro de
qualquer pedido (exigir_perfil), não pode ser uma ida à base de dados de
cada vez. Quem edita limpa a cache da própria instância; as outras
apanham o nome novo no máximo 60 s depois.
"""
import time

from sqlalchemy import select

_TTL_SEGUNDOS = 60
_cache: dict[str, str] = {}
_carregado_em = 0.0


async def obter_nomes() -> dict[str, str]:
    global _cache, _carregado_em
    if _cache and time.monotonic() - _carregado_em < _TTL_SEGUNDOS:
        return _cache
    from app.database.session import AsyncSessionLocalSistema
    from app.database.models_permissoes import PerfilNome
    try:
        async with AsyncSessionLocalSistema() as db:
            linhas = (await db.execute(select(PerfilNome.codigo, PerfilNome.nome))).all()
        _cache = {codigo: nome for codigo, nome in linhas}
        _carregado_em = time.monotonic()
    except Exception:
        # Sem base de dados não há nomes personalizados — os códigos servem.
        pass
    return _cache


async def nome(codigo: str) -> str:
    return (await obter_nomes()).get(codigo, codigo.replace("_", " ").title())


def invalidar() -> None:
    global _carregado_em
    _carregado_em = 0.0
