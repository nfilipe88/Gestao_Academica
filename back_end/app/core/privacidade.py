"""Privacidade e retenção — parte técnica (ver POLITICA_PRIVACIDADE_RASCUNHO.md).

Duas coisas independentes do parecer jurídico:

1. VERSAO_TERMOS: identifica a versão da Política de Privacidade/Termos que
   a escola aceitou no registo (gravada em Tenant.termos_versao). Enquanto a
   política for um rascunho, o valor começa por "rascunho" — trocar por uma
   versão real (e mudar o texto em features/public/privacidade) quando o
   jurista aprovar.

2. limpar_dados_operacionais: apaga só dados que NÃO são registo escolar —
   tokens já inúteis, histórico de IP de logins antigos, notificações lidas
   antigas e candidaturas (leads) que nunca se converteram em aluno. NUNCA
   toca em alunos, matrículas, notas, faturas, documentos ou comunicados:
   esses ficam sujeitos à retenção legal (15 anos, a plataforma desativa,
   nunca elimina).

   Prazo dos leads (15 dias sem atividade): definido pela equipa. Os outros
   prazos são valores técnicos por omissão, **a confirmar pelo jurista** (ver
   POLITICA_PRIVACIDADE_RASCUNHO.md, B.7).
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.database.models_crm import FunilEtapa, LeadCandidato, LeadDocumento, MensagemLead, OportunidadeCRM
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
# Candidaturas que nunca viraram aluno: apagadas (com os documentos anexados,
# incluindo os ficheiros no storage) ao fim deste tempo SEM ATIVIDADE — a
# contagem recomeça sempre que a escola mexe no cartão do funil ou troca
# mensagens com a família, para nunca apagar um lead que está a ser trabalhado.
LEADS_NAO_CONVERTIDOS_RETENCAO_DIAS = int(os.getenv("LEADS_NAO_CONVERTIDOS_RETENCAO_DIAS", "15"))
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

    resumo.update(await _limpar_leads_nao_convertidos(db, agora))

    await db.commit()
    logger.info("Limpeza de dados operacionais: %s", resumo)
    return resumo


async def _limpar_leads_nao_convertidos(db: AsyncSession, agora: datetime) -> dict[str, int]:
    """Apaga leads sem atividade há LEADS_NAO_CONVERTIDOS_RETENCAO_DIAS e que
    nunca viraram aluno (nenhuma oportunidade com aluno gerado nem em etapa
    de ganho). Os ficheiros anexados saem primeiro do storage (as linhas em
    LeadDocumento só apagariam a referência, deixando o ficheiro órfão)."""
    limite = agora - timedelta(days=LEADS_NAO_CONVERTIDOS_RETENCAO_DIAS)

    candidatos = {lead_id: entrada for lead_id, entrada in (await db.execute(
        select(LeadCandidato.id, LeadCandidato.data_entrada).where(LeadCandidato.data_entrada < limite)
    )).all()}
    if not candidatos:
        return {"leads_nao_convertidos": 0, "leads_documentos_ficheiros": 0}
    ids = list(candidatos)

    convertidos = set((await db.execute(
        select(OportunidadeCRM.lead_id)
        .join(FunilEtapa, FunilEtapa.id == OportunidadeCRM.etapa_id)
        .where(OportunidadeCRM.lead_id.in_(ids), or_(OportunidadeCRM.aluno_gerado_id.is_not(None), FunilEtapa.eh_etapa_ganho == True))  # noqa: E712
    )).scalars().all())

    ultima_atividade = dict(candidatos)
    for lead_id, quando in (await db.execute(
        select(OportunidadeCRM.lead_id, func.max(OportunidadeCRM.data_atualizacao))
        .where(OportunidadeCRM.lead_id.in_(ids)).group_by(OportunidadeCRM.lead_id)
    )).all():
        if quando and quando > ultima_atividade[lead_id]:
            ultima_atividade[lead_id] = quando
    for lead_id, quando in (await db.execute(
        select(MensagemLead.lead_id, func.max(MensagemLead.criado_em))
        .where(MensagemLead.lead_id.in_(ids)).group_by(MensagemLead.lead_id)
    )).all():
        if quando and quando > ultima_atividade[lead_id]:
            ultima_atividade[lead_id] = quando

    a_apagar = [i for i in ids if i not in convertidos and ultima_atividade[i] < limite]
    if not a_apagar:
        return {"leads_nao_convertidos": 0, "leads_documentos_ficheiros": 0}

    chaves = (await db.execute(select(LeadDocumento.chave_storage).where(LeadDocumento.lead_id.in_(a_apagar)))).scalars().all()
    for chave in chaves:
        await storage.apagar_ficheiro(chave)

    # oportunidade/documento/mensagem caem em cascata (ON DELETE CASCADE).
    await db.execute(delete(LeadCandidato).where(LeadCandidato.id.in_(a_apagar)))
    return {"leads_nao_convertidos": len(a_apagar), "leads_documentos_ficheiros": len(chaves)}
