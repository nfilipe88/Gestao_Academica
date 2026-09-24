"""Exportação de dados por titular (direito de acesso/portabilidade — ver
POLITICA_PRIVACIDADE_RASCUNHO.md, secção 7).

Dado um titular (aluno, responsável ou utilizador/professor), junta TODOS os
registos da escola que dependem dele, seguindo as chaves estrangeiras da base
de dados em vez de uma lista escrita à mão: assim, uma tabela nova que
referencie o aluno (ou a sua matrícula, fatura, etc.) entra na exportação
sozinha, sem ninguém ter de se lembrar de a acrescentar.

Regras de segurança:
- só se desce pelas dependências (filhos) do titular — nunca se sobe para
  turmas, cursos ou outros alunos. As únicas linhas "para cima" incluídas são
  as contas de utilizador ligadas ao titular e, na exportação de um aluno, os
  dados de contacto dos seus responsáveis; nenhuma delas é seguida mais fundo
  (senão o ficheiro de um aluno traria os contratos dos irmãos);
- tudo filtrado pelo tenant do pedido (além do RLS da sessão);
- nunca saem hashes, tokens nem chaves internas do storage (SEGREDOS), nem as
  tabelas de sessão (TABELAS_IGNORADAS); os ficheiros anexados aparecem só
  com nome/tipo — o conteúdo pode ser pedido à escola.
"""
import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.sqltypes import LargeBinary

from app.database.models import Base

TABELAS_IGNORADAS = {"tenant", "refresh_token", "conta_ativacao_token", "password_reset_token"}
SEGREDOS = {"senha_hash", "token_hash", "chave_storage", "jti"}
_MAX_NIVEIS = 5

# titular -> tabela raiz
RAIZES = {"aluno": "aluno", "responsavel": "responsavel_financeiro_legal", "usuario": "usuario"}


def _tabelas() -> dict[str, Any]:
    return {t.name: t for t in Base.metadata.sorted_tables if t.name not in TABELAS_IGNORADAS}


def _limpar(linha: dict) -> dict:
    return {k: v for k, v in linha.items() if k not in SEGREDOS}


def _colunas_exportaveis(tabela):
    return [c for c in tabela.c if c.name not in SEGREDOS and not isinstance(c.type, LargeBinary)]


async def _linhas(db: AsyncSession, tabela, tenant_id, condicao=None) -> list[dict]:
    consulta = select(*_colunas_exportaveis(tabela))
    if condicao is not None:
        consulta = consulta.where(condicao)
    if "tenant_id" in tabela.c:
        consulta = consulta.where(tabela.c.tenant_id == tenant_id)
    return [dict(r._mapping) for r in (await db.execute(consulta)).all()]


async def exportar_titular(db: AsyncSession, tenant_id: uuid.UUID, tipo: str, titular_id: uuid.UUID) -> dict | None:
    """Devolve {tabela: [linhas]} do titular, ou None se não existir nesta escola."""
    tabelas = _tabelas()
    raiz = tabelas[RAIZES[tipo]]
    ids_raiz = await _linhas(db, raiz, tenant_id, raiz.c.id == titular_id)
    if not ids_raiz:
        return None

    resultado: dict[str, list[dict]] = {raiz.name: ids_raiz}
    ids: dict[str, set] = {raiz.name: {titular_id}}

    # Contas de utilizador ligadas ao titular (dados de login, sem hashes).
    # Passam a ser também ponto de partida da descida: o histórico de logins
    # e as notificações da pessoa fazem parte dos seus dados.
    ligado = ids_raiz[0].get("usuario_id")
    if raiz.name != "usuario" and ligado:
        conta = await _linhas(db, tabelas["usuario"], tenant_id, tabelas["usuario"].c.id == ligado)
        if conta:
            resultado["usuario"] = conta
            ids["usuario"] = {ligado}

    fronteira = set(ids)
    for _ in range(_MAX_NIVEIS):
        novos: dict[str, set] = {}
        for tabela in tabelas.values():
            for fk in tabela.foreign_keys:
                pai = fk.column.table.name
                if pai not in fronteira or fk.column.name != "id" or not ids.get(pai):
                    continue
                encontradas = await _linhas(db, tabela, tenant_id, fk.parent.in_(ids[pai]))
                ja_vistas = {r["id"] for r in resultado.get(tabela.name, []) if "id" in r}
                extra = [r for r in encontradas if r.get("id") not in ja_vistas]
                if not extra:
                    continue
                resultado.setdefault(tabela.name, []).extend(extra)
                if "id" in tabela.c:
                    novos.setdefault(tabela.name, set()).update(r["id"] for r in extra)
        if not novos:
            break
        for nome, conj in novos.items():
            ids.setdefault(nome, set()).update(conj)
        fronteira = set(novos)

    # Só na exportação de um aluno: contactos dos responsáveis (uma linha por
    # vínculo), sem seguir para os contratos/faturas deles.
    if tipo == "aluno" and resultado.get("aluno_responsavel"):
        resp = tabelas["responsavel_financeiro_legal"]
        ids_resp = {r["responsavel_id"] for r in resultado["aluno_responsavel"]}
        resultado["responsavel_financeiro_legal"] = await _linhas(db, resp, tenant_id, resp.c.id.in_(ids_resp))

    return {nome: [_limpar(jsonable_encoder(r)) for r in linhas] for nome, linhas in sorted(resultado.items())}
