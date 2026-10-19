"""Eventos de segurança: tentativas de acesso indevido ficam registadas
com IP e utilizador, quem tem de saber é avisado, e um IP anónimo que
insiste é bloqueado temporariamente. Ver app/core/eventos_seguranca.py."""
from datetime import datetime, timedelta, timezone
import uuid

import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core import fila_notificacoes, privacidade
from app.core.security import ALGORITHM, SECRET_KEY
from app.database.models_usuarios import EventoSeguranca
from app.database.session import AsyncSessionLocalSistema
from main import app
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_auth_rbac import _criar_secretaria_com_token
from tests.test_planos_por_aluno_modulo import _criar_super_admin

_HTML = b"<html><script>alert(1)</script></html>"


def _capturar_emails(monkeypatch) -> list[dict]:
    enviados: list[dict] = []

    async def _agendar_falso(_funcao_envio, **kwargs):
        enviados.append(kwargs)

    monkeypatch.setattr(fila_notificacoes, "agendar_email", _agendar_falso)
    return enviados


async def _eventos(**filtros) -> list[EventoSeguranca]:
    async with AsyncSessionLocalSistema() as db:
        query = select(EventoSeguranca).order_by(EventoSeguranca.data_evento.desc())
        for campo, valor in filtros.items():
            query = query.where(getattr(EventoSeguranca, campo) == valor)
        return list((await db.execute(query.limit(50))).scalars().all())


def _cliente_de(ip: str) -> AsyncClient:
    """Cliente com outro IP de origem — simula um atacante sem afetar o IP dos outros testes."""
    return AsyncClient(transport=ASGITransport(app=app, client=(ip, 40000)), base_url="http://teste.local")


def _ip_unico() -> str:
    n = uuid.uuid4().int
    return f"203.0.{(n >> 8) % 250}.{n % 250 + 1}"


# ==========================================
# Tokens
# ==========================================
async def test_token_forjado_fica_registado_mas_o_expirado_nao(client):
    ip = _ip_unico()
    forjado = jwt.encode({"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()), "perfil_acesso": "SUPER_ADMIN"},
                         "chave-do-atacante-que-nao-e-a-do-servidor-1234567890", algorithm=ALGORITHM)
    expirado = jwt.encode({"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()), "perfil_acesso": "GESTOR",
                           "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, SECRET_KEY, algorithm=ALGORITHM)
    async with _cliente_de(ip) as atacante:
        assert (await atacante.get("/api/v1/perfil", headers=auth_headers(forjado))).status_code == 401
        assert (await atacante.get("/api/v1/perfil", headers=auth_headers(expirado))).status_code == 401

    eventos = await _eventos(ip=ip)
    assert [e.tipo for e in eventos] == ["TOKEN_FORJADO"]
    assert eventos[0].gravidade == "ALTA" and eventos[0].caminho == "/api/v1/perfil"


# ==========================================
# Acesso a áreas sem permissão
# ==========================================
async def test_acesso_negado_regista_o_utilizador_e_avisa_o_gestor(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "seg-acesso-negado")
    headers_gestor = auth_headers(escola["token"])
    token_secretaria = await _criar_secretaria_com_token(client, headers_gestor, escola["nif"])

    resp = await client.get("/api/v1/usuarios", headers=auth_headers(token_secretaria))
    assert resp.status_code == 403

    # O Gestor vê o evento da própria escola, com quem tentou.
    resp = await client.get("/api/v1/seguranca/eventos", headers=headers_gestor)
    assert resp.status_code == 200, resp.text
    evento = next(e for e in resp.json()["items"] if e["tipo"] == "ACESSO_NEGADO")
    assert evento["email"] == f"sec.{escola['nif']}@teste.pt"
    assert evento["caminho"] == "/api/v1/usuarios" and evento["ip"]
    assert any(e["destinatario"] == escola["email"] and "segurança" in e["assunto"].lower() for e in enviados)

    # Outra escola não vê nada disto; a Secretaria não tem acesso ao registo.
    outra = await criar_escola_e_gestor(client, "seg-outra-escola")
    itens = (await client.get("/api/v1/seguranca/eventos", headers=auth_headers(outra["token"]))).json()["items"]
    assert all(e["tenant_id"] == outra["tenant_id"] for e in itens)
    assert (await client.get("/api/v1/seguranca/eventos", headers=auth_headers(token_secretaria))).status_code == 403


async def test_acesso_negado_de_utilizador_identificado_nao_bloqueia_o_ip_da_escola(client):
    escola = await criar_escola_e_gestor(client, "seg-nao-bloqueia")
    token_secretaria = await _criar_secretaria_com_token(client, auth_headers(escola["token"]), escola["nif"])
    for _ in range(15):  # 15 × MEDIA = 45 pontos, se contasse
        await client.get("/api/v1/usuarios", headers=auth_headers(token_secretaria))
    assert (await client.get("/api/v1/perfil", headers=auth_headers(escola["token"]))).status_code == 200


# ==========================================
# Endereços de sondagem / ataque
# ==========================================
async def test_enderecos_de_sondagem_e_ataque_ficam_registados(client):
    ip = _ip_unico()
    async with _cliente_de(ip) as atacante:
        assert (await atacante.get("/.env")).status_code == 404
        assert (await atacante.get("/api/v1/alunos", params={"q": "../../etc/passwd"})).status_code == 404
        assert (await atacante.get("/api/v1/public/config", params={"x": "1' or '1'='1"})).status_code == 404
    gravidades = sorted(e.gravidade for e in await _eventos(ip=ip, tipo="SONDAGEM"))
    assert gravidades == ["ALTA", "ALTA", "MEDIA"]


async def test_pesquisas_normais_nao_disparam(client):
    escola = await criar_escola_e_gestor(client, "seg-pesquisa-normal")
    for termo in ("select", "union", "Ana d'Oliveira", "2024/2025"):
        resp = await client.get("/api/v1/alunos", headers=auth_headers(escola["token"]), params={"q": termo})
        assert resp.status_code == 200, (termo, resp.text)


# ==========================================
# Ficheiros maliciosos
# ==========================================
async def test_ficheiro_malicioso_regista_quem_o_enviou(client, monkeypatch):
    _capturar_emails(monkeypatch)
    escola = await criar_escola_e_gestor(client, "seg-ficheiro")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/configuracoes/logotipo", headers=headers, files={"ficheiro": ("logo.png", _HTML, "image/png")})
    assert resp.status_code == 400
    # Um engano honesto (PDF onde se pede uma imagem) é recusado mas não é um evento.
    resp = await client.put("/api/v1/configuracoes/logotipo", headers=headers, files={"ficheiro": ("doc.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert resp.status_code == 400

    eventos = await _eventos(tenant_id=uuid.UUID(escola["tenant_id"]), tipo="FICHEIRO_MALICIOSO")
    assert len(eventos) == 1
    assert eventos[0].email == escola["email"] and "logo.png" in eventos[0].detalhe


# ==========================================
# Força bruta no login
# ==========================================
async def test_login_falhado_regista_o_email_tentado(client):
    escola = await criar_escola_e_gestor(client, "seg-login")
    resp = await client.post("/api/v1/auth/login", data={"username": escola["email"], "password": "Errada12345!"})
    assert resp.status_code == 401
    evento = (await _eventos(tenant_id=uuid.UUID(escola["tenant_id"]), tipo="LOGIN_FALHADO"))[0]
    assert evento.email == escola["email"] and evento.usuario_id is None


# ==========================================
# Bloqueio temporário de IP
# ==========================================
async def test_ip_anonimo_que_insiste_e_bloqueado_e_o_super_admin_desbloqueia(client, monkeypatch):
    enviados = _capturar_emails(monkeypatch)
    super_admin = await _criar_super_admin(client)
    headers_sa = auth_headers(super_admin["access_token"])
    ip = _ip_unico()

    async with _cliente_de(ip) as atacante:
        for _ in range(3):  # 3 × ALTA = 30 pontos = limite
            await atacante.get("/api/v1/alunos", params={"q": "../../etc/passwd"})
        resp = await atacante.get("/api/v1/public/config")
        assert resp.status_code == 403 and "bloqueado" in resp.json()["detail"]
        # O healthcheck nunca é bloqueado (monitorização/balanceador).
        assert (await atacante.get("/api/v1/health")).status_code == 200

    # O resto da plataforma não é afetado.
    assert (await client.get("/api/v1/public/config")).status_code == 200

    bloqueios = (await client.get("/api/v1/admin/seguranca/bloqueios", headers=headers_sa)).json()
    assert any(b["ip"] == ip for b in bloqueios)
    assert [e.tipo for e in await _eventos(ip=ip, tipo="IP_BLOQUEADO")] == ["IP_BLOQUEADO"]
    assert any("IP_BLOQUEADO" in e["assunto"] for e in enviados)

    resp = await client.get("/api/v1/admin/seguranca/eventos", headers=headers_sa, params={"ip": ip})
    assert resp.status_code == 200 and resp.json()["total"] == 4

    assert (await client.delete(f"/api/v1/admin/seguranca/bloqueios/{ip}", headers=headers_sa)).status_code == 200
    async with _cliente_de(ip) as ex_atacante:
        assert (await ex_atacante.get("/api/v1/public/config")).status_code == 200


# ==========================================
# Retenção (o IP é dado pessoal)
# ==========================================
async def test_eventos_antigos_sao_apagados_pela_limpeza_diaria():
    antigo_id = uuid.uuid4()
    async with AsyncSessionLocalSistema() as db:
        db.add(EventoSeguranca(
            id=antigo_id, tipo="SONDAGEM", gravidade="MEDIA", ip="198.51.100.7",
            data_evento=datetime.now(timezone.utc) - timedelta(days=privacidade.SEGURANCA_EVENTOS_RETENCAO_DIAS + 1),
        ))
        await db.commit()
        await privacidade.limpar_dados_operacionais(db)
        assert (await db.get(EventoSeguranca, antigo_id)) is None
