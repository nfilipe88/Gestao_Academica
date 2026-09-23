"""Parte técnica da privacidade (ver app/core/privacidade.py e
POLITICA_PRIVACIDADE_RASCUNHO.md): aceitação dos termos no registo e limpeza
de dados OPERACIONAIS — nunca de registos escolares."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core import privacidade
from app.database.models import Tenant
from app.database.models_notificacoes import Notificacao
from app.database.models_pessoas import Aluno
from app.database.models_usuarios import ContaAtivacaoToken, LoginHistorico, RefreshToken
from app.database.session import AsyncSessionLocalSistema
from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def test_registo_sem_aceitar_os_termos_e_recusado(client):
    suf = sufixo_unico()
    resp = await client.post("/api/v1/auth/registo", json={
        "nome_fantasia": f"Escola Sem Termos {suf}", "nif": suf, "nome_gestor": "Gestor",
        "email_gestor": f"semtermos.{suf}@teste.pt", "palavra_passe": "SenhaTeste123!",
    })
    assert resp.status_code == 400
    assert "Política de Privacidade" in resp.json()["detail"]


async def test_registo_grava_a_versao_e_a_data_dos_termos_aceites(client):
    escola = await criar_escola_e_gestor(client, "termos-gravados")
    async with AsyncSessionLocalSistema() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(escola["tenant_id"])))).scalar_one()
    assert tenant.termos_versao == privacidade.VERSAO_TERMOS
    assert tenant.termos_aceites_em is not None


async def test_limpeza_operacional_apaga_so_o_antigo_e_nunca_registos_escolares(client):
    escola = await criar_escola_e_gestor(client, "limpeza-operacional")
    tenant_id = uuid.UUID(escola["tenant_id"])
    usuario_id = uuid.UUID(escola["usuario_id"])
    agora = datetime.now(timezone.utc)
    velho = agora - timedelta(days=max(privacidade.LOGIN_HISTORICO_RETENCAO_DIAS, privacidade.NOTIFICACOES_LIDAS_RETENCAO_DIAS, privacidade.TOKENS_RETENCAO_DIAS) + 5)
    recente = agora - timedelta(days=2)

    aluno = (await client.post("/api/v1/alunos", headers=auth_headers(escola["token"]), json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": "Aluno Intocável", "data_nascimento": "2012-01-01"})).json()["id"]

    async with AsyncSessionLocalSistema() as db:
        login_velho = LoginHistorico(tenant_id=tenant_id, usuario_id=usuario_id, ip="10.0.0.1", data_login=velho)
        login_recente = LoginHistorico(tenant_id=tenant_id, usuario_id=usuario_id, ip="10.0.0.2", data_login=recente)
        notif_lida_velha = Notificacao(tenant_id=tenant_id, usuario_id=usuario_id, tipo="X", titulo="velha lida", mensagem="m", lida=True, data_criacao=velho)
        notif_nao_lida_velha = Notificacao(tenant_id=tenant_id, usuario_id=usuario_id, tipo="X", titulo="velha por ler", mensagem="m", lida=False, data_criacao=velho)
        notif_lida_recente = Notificacao(tenant_id=tenant_id, usuario_id=usuario_id, tipo="X", titulo="recente lida", mensagem="m", lida=True, data_criacao=recente)
        token_expirado = ContaAtivacaoToken(tenant_id=tenant_id, usuario_id=usuario_id, token_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32], expira_em=velho)
        token_valido = RefreshToken(tenant_id=tenant_id, usuario_id=usuario_id, token_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32], expira_em=agora + timedelta(days=5))
        db.add_all([login_velho, login_recente, notif_lida_velha, notif_nao_lida_velha, notif_lida_recente, token_expirado, token_valido])
        await db.commit()
        ids = {k: v.id for k, v in dict(
            login_velho=login_velho, login_recente=login_recente, notif_lida_velha=notif_lida_velha,
            notif_nao_lida_velha=notif_nao_lida_velha, notif_lida_recente=notif_lida_recente,
            token_expirado=token_expirado, token_valido=token_valido).items()}

    async with AsyncSessionLocalSistema() as db:
        resumo = await privacidade.limpar_dados_operacionais(db)
    assert resumo["login_historico"] >= 1 and resumo["notificacoes_lidas"] >= 1 and resumo["tokens_ativacao"] >= 1

    async with AsyncSessionLocalSistema() as db:
        async def existe(modelo, chave):
            return (await db.execute(select(modelo.id).where(modelo.id == ids[chave]))).first() is not None
        assert not await existe(LoginHistorico, "login_velho")
        assert await existe(LoginHistorico, "login_recente")
        assert not await existe(Notificacao, "notif_lida_velha")
        assert await existe(Notificacao, "notif_nao_lida_velha"), "notificações por ler nunca são apagadas"
        assert await existe(Notificacao, "notif_lida_recente")
        assert not await existe(ContaAtivacaoToken, "token_expirado")
        assert await existe(RefreshToken, "token_valido")
        assert (await db.execute(select(Aluno.id).where(Aluno.id == uuid.UUID(aluno)))).first() is not None, \
            "a limpeza operacional nunca pode tocar em registos escolares"


# ==========================================
# Candidaturas (leads) não convertidas — 15 dias sem atividade
# ==========================================
from sqlalchemy import update  # noqa: E402

from app.core import storage  # noqa: E402
from app.database.models_crm import LeadCandidato, LeadDocumento, MensagemLead, OportunidadeCRM  # noqa: E402
from tests.test_crm import _PNG_1X1  # noqa: E402


async def _criar_lead(client, escola, nome: str, com_documento: bool = False) -> uuid.UUID:
    resp = await client.post(f"/api/v1/public/{escola['tenant_id']}/leads", json={
        "nome_responsavel": nome, "nome_aluno_candidato": f"Candidato {nome}",
        "email_contato": f"lead.{sufixo_unico()}@teste.pt"})
    assert resp.status_code == 201, resp.text
    lead_id = resp.json()["id"]
    if com_documento:
        resp = await client.post(
            f"/api/v1/public/{escola['tenant_id']}/leads/{lead_id}/documentos", params={"tipo": "BI"},
            files={"ficheiro": ("bi.png", _PNG_1X1, "image/png")})
        assert resp.status_code == 201, resp.text
    return uuid.UUID(lead_id)


async def _envelhecer_lead(lead_id: uuid.UUID, dias: int) -> None:
    """Recua a entrada E a atividade do cartão do funil (criada agora, contaria como atividade recente)."""
    antigo = datetime.now(timezone.utc) - timedelta(days=dias)
    async with AsyncSessionLocalSistema() as db:
        await db.execute(update(LeadCandidato).where(LeadCandidato.id == lead_id).values(data_entrada=antigo))
        await db.execute(update(OportunidadeCRM).where(OportunidadeCRM.lead_id == lead_id).values(data_atualizacao=antigo))
        await db.commit()


async def _lead_existe(lead_id: uuid.UUID) -> bool:
    async with AsyncSessionLocalSistema() as db:
        return (await db.execute(select(LeadCandidato.id).where(LeadCandidato.id == lead_id))).first() is not None


async def test_lead_nao_convertido_sem_atividade_e_apagado_com_os_ficheiros(client):
    escola = await criar_escola_e_gestor(client, "lead-15-dias")
    lead_id = await _criar_lead(client, escola, "Antigo", com_documento=True)
    async with AsyncSessionLocalSistema() as db:
        chave = (await db.execute(select(LeadDocumento.chave_storage).where(LeadDocumento.lead_id == lead_id))).scalar_one()
    assert await storage.obter_ficheiro(chave) is not None

    await _envelhecer_lead(lead_id, privacidade.LEADS_NAO_CONVERTIDOS_RETENCAO_DIAS + 2)
    async with AsyncSessionLocalSistema() as db:
        resumo = await privacidade.limpar_dados_operacionais(db)

    assert resumo["leads_nao_convertidos"] >= 1
    assert not await _lead_existe(lead_id)
    assert await storage.obter_ficheiro(chave) is None, "o ficheiro anexado também tem de sair do storage"


async def test_lead_recente_ou_com_atividade_recente_ou_convertido_nao_e_apagado(client):
    escola = await criar_escola_e_gestor(client, "lead-15-dias-poupados")
    headers = auth_headers(escola["token"])
    recente = await _criar_lead(client, escola, "Recente")
    com_mensagem = await _criar_lead(client, escola, "ComMensagem")
    convertido = await _criar_lead(client, escola, "Convertido")
    for lead in (com_mensagem, convertido):
        await _envelhecer_lead(lead, privacidade.LEADS_NAO_CONVERTIDOS_RETENCAO_DIAS + 30)

    resp = await client.post(f"/api/v1/crm/leads/{com_mensagem}/mensagens", headers=headers, json={"corpo": "Olá, ainda a tratar disto."})
    assert resp.status_code == 201, resp.text

    aluno_id = uuid.UUID((await client.post("/api/v1/alunos", headers=headers, json={
        "matricula_interna": f"AL{sufixo_unico()}", "nome_completo": "Aluno Convertido", "data_nascimento": "2012-01-01"})).json()["id"])
    async with AsyncSessionLocalSistema() as db:
        await db.execute(update(OportunidadeCRM).where(OportunidadeCRM.lead_id == convertido).values(aluno_gerado_id=aluno_id))
        await db.commit()

    async with AsyncSessionLocalSistema() as db:
        await privacidade.limpar_dados_operacionais(db)

    assert await _lead_existe(recente), "lead recente nunca é apagado"
    assert await _lead_existe(com_mensagem), "uma resposta recente da escola conta como atividade"
    assert await _lead_existe(convertido), "lead já convertido em aluno nunca é apagado"
