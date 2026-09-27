"""Isolamento multi-tenant do webhook do PayPal (app/cruds/financeiro.py::
processar_webhook_paypal) — o único sítio da app que recebe uma chamada
verdadeiramente sem sessão nenhuma (nem token, nem tenant_id no path), numa
sessão bypassrls (ver app/database/session.py::obter_sessao_db_publica).

Criar uma TransacaoGateway real passaria pela PayPal Orders API de verdade
(app/core/paypal.py::criar_order) — em vez disso, insere-se a linha
diretamente (mesmo atalho já usado noutros testes para pré-condições difíceis
de alcançar pela API, ex.: tests/test_privacidade.py) e mono-corrige-se
verificar_assinatura_webhook para simular uma assinatura válida — o que
importa aqui é a lógica de isolamento e de correspondência por
gateway_transaction_id, não a integração HTTP com a PayPal em si."""
import uuid
from datetime import date

from sqlalchemy import select

from app.core import fila_notificacoes
from app.cruds import financeiro as crud_financeiro
from app.database.models_financeiro import FaturaMensalidade, TransacaoGateway
from app.database.session import AsyncSessionLocalSistema
from tests.conftest import auth_headers, criar_escola_e_gestor
from tests.test_recibo_pagamento import _preparar_contrato_com_2_parcelas


async def _preparar_fatura_com_transacao(client, prefixo: str, order_id: str) -> dict:
    escola = await criar_escola_e_gestor(client, prefixo)
    headers = auth_headers(escola["token"])
    faturas = await _preparar_contrato_com_2_parcelas(client, headers, date.today().year)
    fatura_id = uuid.UUID(faturas[0]["id"])

    async with AsyncSessionLocalSistema() as db:
        db.add(TransacaoGateway(
            tenant_id=uuid.UUID(escola["tenant_id"]), fatura_id=fatura_id, metodo_pagamento="PAYPAL",
            gateway_transaction_id=order_id, status="AGUARDANDO_PAGAMENTO",
            dados_cobranca={"valor": "60000.00"},
        ))
        await db.commit()

    return {"escola": escola, "headers": headers, "fatura_id": fatura_id, "order_id": order_id}


def _evento_captura_completa(order_id: str) -> dict:
    return {
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "amount": {"value": "60000.00", "currency_code": "AOA"},
            "supplementary_data": {"related_ids": {"order_id": order_id}},
        },
    }


async def _status_da_fatura(fatura_id: uuid.UUID) -> str:
    # Não há GET /financeiro/faturas/{id} isolado — vai direto à BD (sessão de
    # sistema, só leitura) em vez de reaproveitar a listagem do contrato.
    async with AsyncSessionLocalSistema() as db:
        fatura = (await db.execute(select(FaturaMensalidade).where(FaturaMensalidade.id == fatura_id))).scalar_one()
        return fatura.status_pagamento


async def test_webhook_so_efetiva_o_pagamento_da_escola_dona_da_transacao(client, monkeypatch):
    monkeypatch.setattr("app.core.paypal.verificar_assinatura_webhook", _assinatura_sempre_valida)

    a = await _preparar_fatura_com_transacao(client, "webhook-a", f"ORDER-A-{uuid.uuid4().hex[:12]}")
    b = await _preparar_fatura_com_transacao(client, "webhook-b", f"ORDER-B-{uuid.uuid4().hex[:12]}")

    async with AsyncSessionLocalSistema() as db:
        await crud_financeiro.processar_webhook_paypal(
            db, {}, b"{}", _evento_captura_completa(a["order_id"]), fila_notificacoes.agendar_email
        )

    assert await _status_da_fatura(a["fatura_id"]) == "PAGO"
    assert await _status_da_fatura(b["fatura_id"]) == "PENDENTE", (
        "FALHA DE ISOLAMENTO: o webhook da escola A efetivou também a fatura da escola B."
    )


async def test_webhook_com_order_id_desconhecido_e_ignorado_em_silencio(client, monkeypatch):
    """Nem sequer levanta erro — RN03 exige responder 200 sempre ao PayPal
    (ver docstring da rota); um order_id forjado/de outra integração não
    pode ter efeito nenhum em nenhuma fatura de nenhuma escola."""
    monkeypatch.setattr("app.core.paypal.verificar_assinatura_webhook", _assinatura_sempre_valida)
    a = await _preparar_fatura_com_transacao(client, "webhook-forjado", f"ORDER-REAL-{uuid.uuid4().hex[:12]}")

    async with AsyncSessionLocalSistema() as db:
        await crud_financeiro.processar_webhook_paypal(
            db, {}, b"{}", _evento_captura_completa("ORDER-QUE-NAO-EXISTE"), fila_notificacoes.agendar_email
        )

    assert await _status_da_fatura(a["fatura_id"]) == "PENDENTE"


async def test_webhook_sem_assinatura_valida_nao_altera_nenhuma_fatura(client):
    """Ponta a ponta pela rota HTTP real, sem monkeypatch nenhum: em
    .env.test não há PAYPAL_WEBHOOK_ID configurado, por isso
    verificar_assinatura_webhook devolve False sozinho — a rota pública
    responde 200 (nunca deixa o PayPal em retry-loop) mas não toca em nada."""
    a = await _preparar_fatura_com_transacao(client, "webhook-sem-assinatura", f"ORDER-SEM-ASSIN-{uuid.uuid4().hex[:12]}")

    resp = await client.post("/api/v1/webhooks/paypal/pagamentos", json=_evento_captura_completa(a["order_id"]))
    assert resp.status_code == 200, resp.text

    assert await _status_da_fatura(a["fatura_id"]) == "PENDENTE"


async def _assinatura_sempre_valida(*_a, **_k) -> bool:
    return True
