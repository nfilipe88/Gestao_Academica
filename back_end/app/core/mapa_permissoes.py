"""
Mapa de Permissões a sério: cada pedido a um módulo de uma escola é
confirmado contra o mapa (módulo × perfil × operação) antes de a rota
correr.

O mapa só RESTRINGE: a permissão efetiva é "o código permite" (o
exigir_perfil de cada rota, que também decide QUE dados cada perfil vê —
ex.: o Professor só as suas turmas) E "o mapa permite". Nunca dá a um
perfil mais do que o código lhe dá — por isso o ecrã mostra bloqueadas as
células acima do teto do código (teto_do_codigo, calculado a partir das
próprias rotas).

Três camadas, sempre a restringir:
  1. mapa base (permissao_modulo, global) — o Super Admin;
  2. mapa da escola (permissao_modulo_escola) — o Gestor, só dentro do base;
  3. perfil da escola (perfil_personalizado) — dentro dos dois anteriores.

Fora do mapa, de propósito: autenticação, perfil próprio, notificações,
páginas públicas, Gestão de Acessos (uma escola nunca perde, pelo mapa,
o controlo das próprias contas) e a equipa da plataforma (Super Admin e
Suporte nunca são restringidos pelo mapa).
"""
import time

from fastapi import HTTPException, Request, status
from fastapi.routing import APIRoute

# Módulo do mapa de cada zona da API (o prefixo mais comprido ganha).
_MODULOS_POR_CAMINHO: list[tuple[str, str]] = sorted([
    ("/api/v1/academico/turmas", "Turmas & Matrículas"),
    ("/api/v1/turmas", "Turmas & Matrículas"),
    ("/api/v1/matriculas", "Turmas & Matrículas"),
    ("/api/v1/fecho", "Turmas & Matrículas"),
    ("/api/v1/academico", "Cursos"),
    ("/api/v1/alunos", "Alunos & Responsáveis"),
    ("/api/v1/responsaveis", "Alunos & Responsáveis"),
    ("/api/v1/diario", "Diário de Classe"),
    ("/api/v1/importacao", "Diário de Classe"),
    ("/api/v1/comportamento", "Comportamento"),
    ("/api/v1/tarefas", "Trabalhos / Tarefas"),
    ("/api/v1/lms", "Trabalhos / Tarefas"),
    ("/api/v1/horarios", "Horários"),
    ("/api/v1/comunicados", "Comunicações"),
    ("/api/v1/documentos", "Documentos (interno)"),
    ("/api/v1/crm", "CRM"),
    ("/api/v1/financeiro", "Financeiro"),
    ("/api/v1/propinas", "Financeiro"),
    ("/api/v1/transferencias", "Transferências de Alunos"),
    ("/api/v1/professores", "Professores"),
    ("/api/v1/indicadores", "Indicadores"),
    ("/api/v1/estatisticas", "Estatísticas"),
    ("/api/v1/configuracoes", "Configurações"),
    ("/api/v1/calendario", "Configurações"),
    ("/api/v1/eventos", "Configurações"),
    ("/api/v1/portal", "Portal (próprio / educandos)"),
], key=lambda par: len(par[0]), reverse=True)

# Coluna do mapa de cada perfil (Aluno e Responsável partilham uma coluna).
COLUNA_DO_PERFIL = {
    "SUPER_ADMIN": "super_admin", "GESTOR": "gestor", "SECRETARIA": "secretaria",
    "PROFESSOR": "professor", "ALUNO": "aluno_responsavel", "RESPONSAVEL": "aluno_responsavel",
}
PERFIS_DA_COLUNA = {
    "super_admin": {"SUPER_ADMIN"}, "gestor": {"GESTOR"}, "secretaria": {"SECRETARIA"},
    "professor": {"PROFESSOR"}, "aluno_responsavel": {"ALUNO", "RESPONSAVEL"},
}
# A equipa da plataforma nunca é restringida pelo mapa (e o Super Admin não
# se pode trancar fora): o acesso dela continua a ser decidido só no código.
PERFIS_FORA_DO_MAPA = {"SUPER_ADMIN", "SUPORTE"}

OPERACOES = ("pode_criar", "pode_ler", "pode_atualizar", "pode_apagar")
_OPERACAO_DO_METODO = {"GET": "pode_ler", "HEAD": "pode_ler", "POST": "pode_criar",
                       "PUT": "pode_atualizar", "PATCH": "pode_atualizar", "DELETE": "pode_apagar"}
NOME_OPERACAO = {"pode_criar": "criar", "pode_ler": "ver", "pode_atualizar": "alterar", "pode_apagar": "apagar"}

# O Gestor nunca pode perder, pelo mapa, o acesso às Configurações da escola.
PROTEGIDOS = {("Configurações", "gestor", "pode_ler"), ("Configurações", "gestor", "pode_atualizar")}


def modulo_do_caminho(caminho: str) -> str | None:
    for prefixo, modulo in _MODULOS_POR_CAMINHO:
        if caminho == prefixo or caminho.startswith(prefixo + "/"):
            return modulo
    return None


def operacao_do_metodo(metodo: str) -> str | None:
    return _OPERACAO_DO_METODO.get(metodo.upper())


# ==========================================
# Teto do código: o que cada rota deixa cada perfil fazer
# ==========================================
def _perfis_da_rota(rota: APIRoute) -> set[str] | None:
    """Perfis que esta rota aceita (interseção de todos os exigir_perfil
    da árvore de dependências); todos os perfis se só exigir sessão;
    None se for pública."""
    from app.core.security import obter_utilizador_atual
    conjuntos: list[frozenset] = []
    exige_sessao = False
    pendentes = list(rota.dependant.dependencies)
    while pendentes:
        dep = pendentes.pop()
        chamada = dep.call
        if getattr(chamada, "perfis_permitidos", None) is not None:
            conjuntos.append(chamada.perfis_permitidos)
        if chamada is obter_utilizador_atual:
            exige_sessao = True
        pendentes.extend(dep.dependencies)
    if conjuntos:
        resultado = set(conjuntos[0])
        for c in conjuntos[1:]:
            resultado &= c
        return resultado
    if exige_sessao:
        return set(COLUNA_DO_PERFIL) | PERFIS_FORA_DO_MAPA
    return None


def _rotas_api(app) -> list[APIRoute]:
    rotas, pendentes = [], list(app.router.routes)
    while pendentes:
        rota = pendentes.pop()
        if isinstance(rota, APIRoute):
            rotas.append(rota)
        elif hasattr(rota, "original_router"):  # router incluído (FastAPI 0.14x)
            pendentes.extend(rota.original_router.routes)
        elif hasattr(rota, "routes"):
            pendentes.extend(rota.routes)
    return rotas


def teto_do_codigo(app) -> dict[tuple[str, str], dict[str, bool]]:
    """{(modulo, coluna): {operacao: o código permite?}} — a célula fica
    permitida se ALGUMA rota desse módulo, com essa operação, aceita o perfil."""
    teto: dict[tuple[str, str], dict[str, bool]] = {}
    for rota in _rotas_api(app):
        modulo = modulo_do_caminho(rota.path)
        perfis = _perfis_da_rota(rota) if modulo else None
        if not modulo or perfis is None:
            continue
        for metodo in rota.methods or ():
            operacao = operacao_do_metodo(metodo)
            if not operacao:
                continue
            for coluna, perfis_coluna in PERFIS_DA_COLUNA.items():
                celula = teto.setdefault((modulo, coluna), {op: False for op in OPERACOES})
                if perfis & perfis_coluna:
                    celula[operacao] = True
    return teto


# ==========================================
# Permissão efetiva (cache curta: é consultada em cada pedido)
# ==========================================
_TTL_SEGUNDOS = 30
_cache_base: tuple[float, dict] = (0.0, {})
_cache_escola: dict[str, tuple[float, dict]] = {}
_cache_perfil_usuario: dict[str, tuple[float, object]] = {}


def invalidar_cache() -> None:
    global _cache_base
    _cache_base = (0.0, {})
    _cache_escola.clear()
    _cache_perfil_usuario.clear()


async def _mapa_base() -> dict:
    global _cache_base
    if time.monotonic() - _cache_base[0] < _TTL_SEGUNDOS:
        return _cache_base[1]
    from sqlalchemy import select
    from app.database.session import AsyncSessionLocalSistema
    from app.database.models_permissoes import PermissaoModulo
    async with AsyncSessionLocalSistema() as db:
        linhas = (await db.execute(select(PermissaoModulo))).scalars().all()
    mapa = {(l.modulo, l.perfil): {op: getattr(l, op) for op in OPERACOES} for l in linhas}
    _cache_base = (time.monotonic(), mapa)
    return mapa


async def _restricoes_escola(tenant_id) -> dict:
    chave = str(tenant_id)
    em_cache = _cache_escola.get(chave)
    if em_cache and time.monotonic() - em_cache[0] < _TTL_SEGUNDOS:
        return em_cache[1]
    from sqlalchemy import select
    from app.database.session import AsyncSessionLocalSistema
    from app.database.models_permissoes import PermissaoModuloEscola
    async with AsyncSessionLocalSistema() as db:
        linhas = (await db.execute(
            select(PermissaoModuloEscola).where(PermissaoModuloEscola.tenant_id == tenant_id)
        )).scalars().all()
    mapa = {(l.modulo, l.perfil): {op: getattr(l, op) for op in OPERACOES} for l in linhas}
    _cache_escola[chave] = (time.monotonic(), mapa)
    return mapa


async def permissao_efetiva(tenant_id, perfil_acesso: str, modulo: str, operacao: str, usuario_id=None) -> bool:
    if perfil_acesso in PERFIS_FORA_DO_MAPA:
        return True
    coluna = COLUNA_DO_PERFIL.get(perfil_acesso)
    if coluna is None:
        return True
    if (modulo, coluna, operacao) in PROTEGIDOS:
        return True
    base = (await _mapa_base()).get((modulo, coluna))
    if base is not None and not base.get(operacao, False):
        return False
    da_escola = (await _restricoes_escola(tenant_id)).get((modulo, coluna))
    if da_escola is not None and not da_escola.get(operacao, False):
        return False
    return True


async def verificar_mapa(request: Request) -> None:
    """Dependência global (main.py): corre antes de cada rota. Pedidos sem
    sessão, fora dos módulos do mapa ou com um token que não se lê seguem
    para a própria rota, que decide (401, rota pública, …)."""
    modulo = modulo_do_caminho(request.url.path)
    operacao = operacao_do_metodo(request.method)
    autorizacao = request.headers.get("authorization", "")
    if not modulo or not operacao or not autorizacao.lower().startswith("bearer "):
        return
    import jwt
    from app.core.security import ALGORITHM, SECRET_KEY
    try:
        claims = jwt.decode(autorizacao[7:].strip(), SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return  # a rota trata (e regista, se for forjado)
    perfil, tenant_id = claims.get("perfil_acesso"), claims.get("tenant_id")
    if not perfil or not tenant_id:
        return
    if await permissao_efetiva(tenant_id, perfil, modulo, operacao, claims.get("sub")):
        return

    import uuid
    from app.core import eventos_seguranca, nomes_perfil
    nome_perfil = await nomes_perfil.nome(perfil)
    # Com o utilizador identificado: é uma pessoa da escola, nunca conta para
    # bloquear o IP (ver eventos_seguranca) — vai para o registo e para o Gestor.
    await eventos_seguranca.registar(
        eventos_seguranca.ACESSO_NEGADO, eventos_seguranca.MEDIA,
        f"Mapa de Permissões: {nome_perfil} sem permissão para {NOME_OPERACAO[operacao]} em {modulo}.",
        usuario_id=uuid.UUID(claims["sub"]), tenant_id=uuid.UUID(tenant_id),
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"O seu perfil ({nome_perfil}) não tem permissão para {NOME_OPERACAO[operacao]} em {modulo}.",
    )
