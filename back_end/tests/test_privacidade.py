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
