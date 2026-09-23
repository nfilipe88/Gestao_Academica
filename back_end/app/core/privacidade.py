"""Privacidade e retenção — parte técnica (ver POLITICA_PRIVACIDADE_RASCUNHO.md).

Duas coisas independentes do parecer jurídico:

1. VERSAO_TERMOS: identifica a versão da Política de Privacidade/Termos que
   a escola aceitou no registo (gravada em Tenant.termos_versao). Enquanto a
   política for um rascunho, o valor começa por "rascunho" — trocar por uma
   versão real (e mudar o texto em features/public/privacidade) quando o
   jurista aprovar.

2. limpar_dados_operacionais: apaga só dados OPERACIONAIS que crescem sem
   limite e não são registo escolar — tokens já inúteis, histórico de IP de
   logins antigos e notificações lidas antigas. NUNCA toca em alunos,
   matrículas, notas, faturas, documentos, comunicados ou leads: esses ficam
   sujeitos à retenção legal (a plataforma desativa, nunca elimina).

   Os prazos abaixo são valores técnicos por omissão, **a confirmar pelo
   jurista** (ver POLITICA_PRIVACIDADE_RASCUNHO.md, B.7).
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_notificacoes import Notificacao
from app.database.models_usuarios import ContaAtivacaoToken, LoginHistorico, PasswordResetToken, RefreshToken

logger = logging.getLogger("privacidade")

VERSAO_TERMOS = "rascunho-2026-09"

# Histórico de IP/navegador por login. Alimenta o alerta "novo login detetado":
# passado este prazo, um IP antigo volta a ser tratado como novo (um alerta a
# mais, sem consequências).
LOGIN_HISTORICO_RETENCAO_DIAS = int(os.getenv("LOGIN_HISTORICO_RETENCAO_DIAS", "365"))
# Só notificações JÁ LIDAS — as por ler nunca são apagadas.
NOTIFICACOES_LIDAS_RETENCAO_DIAS = int(os.getenv("NOTIFICACOES_LIDAS_RETENCAO_DIAS", "180"))
# Tokens expirados/usados/revogados ficam este tempo (para auditar incidentes) e depois saem.
TOKENS_RETENCAO_DIAS = int(os.getenv("TOKENS_RETENCAO_DIAS", "30"))


async def limpar_dados_operacionais(db: AsyncSession, agora: datetime | None = None) -> dict[str, int]:
    """Devolve quantas linhas foram apagadas por categoria. Deve correr numa
    sessão de sistema (bypassrls): é uma limpeza cross-escola."""
    agora = agora or datetime.now(timezone.utc)
    limite_tokens = agora - timedelta(days=TOKENS_RETENCAO_DIAS)
    resumo: dict[str, int] = {}

    for nome, modelo, usado_ou_revogado in (
        ("tokens_ativacao", ContaAtivacaoToken, ContaAtivacaoToken.usado),
        ("tokens_redefinicao_senha", PasswordResetToken, PasswordResetToken.usado),
        ("refresh_tokens", RefreshToken, RefreshToken.revogado),
    ):
        resultado = await db.execute(
            delete(modelo).where(or_(
                modelo.expira_em < limite_tokens,
                (usado_ou_revogado == True) & (modelo.data_criacao < limite_tokens),  # noqa: E712
            ))
        )
        resumo[nome] = resultado.rowcount or 0

    resultado = await db.execute(
        delete(LoginHistorico).where(LoginHistorico.data_login < agora - timedelta(days=LOGIN_HISTORICO_RETENCAO_DIAS))
    )
    resumo["login_historico"] = resultado.rowcount or 0

    resultado = await db.execute(
        delete(Notificacao).where(
            Notificacao.lida == True,  # noqa: E712
            Notificacao.data_criacao < agora - timedelta(days=NOTIFICACOES_LIDAS_RETENCAO_DIAS),
        )
    )
    resumo["notificacoes_lidas"] = resultado.rowcount or 0

    await db.commit()
    logger.info("Limpeza de dados operacionais: %s", resumo)
    return resumo
