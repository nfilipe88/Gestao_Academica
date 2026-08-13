import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db, obter_sessao_db_publica
from app.core.security import obter_utilizador_atual, exigir_perfil
from app.schemas.financeiro import CapturarPagamentoRequest, ContratoCreate, FaturaMarcarPago, GerarCobrancaRequest
from app.cruds import financeiro as crud_financeiro

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro"])

# Router à parte, sem o prefixo /financeiro e sem exigir autenticação —
# é o PayPal quem chama isto (ver POST /api/v1/webhooks/paypal/pagamentos
# mais abaixo). Registado em main.py como qualquer outro router.
router_webhooks = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

# Só Gestor/Secretaria criam/gerem contratos e mexem em pagamentos — o
# mesmo padrão RBAC usado em matrículas/académico. Leitura (extrato,
# detalhe da fatura) fica aberta a qualquer utilizador autenticado da
# escola (o Portal do Responsável/Aluno, quando existir, vai precisar
# de ler sem ser Gestor).
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")


async def _via_background_tasks(background_tasks: BackgroundTasks):
    """Fábrica do `agendar_email` esperado pelo crud — despacha via BackgroundTasks.add_task."""
    async def agendar(func, **kwargs):
        background_tasks.add_task(func, **kwargs)
    return agendar

# ==========================================
# A. RESPONSÁVEIS ELEGÍVEIS (para o formulário de novo contrato)
# ==========================================
@router.get("/matriculas/{matricula_id}/responsaveis")
async def listar_responsaveis_da_matricula(
    matricula_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os responsáveis do aluno associado a esta matrícula, para escolher quem paga."""
    return await crud_financeiro.listar_responsaveis_da_matricula(db, utilizador["tenant_id"], matricula_id)

# ==========================================
# B. CRIAR CONTRATO FINANCEIRO (E GERAR AS FATURAS)
# ==========================================
@router.post("/contratos", status_code=status.HTTP_201_CREATED)
async def criar_contrato(
    dados: ContratoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """Assina o contrato financeiro do ano letivo e gera de imediato todas as parcelas."""
    return await crud_financeiro.criar_contrato(db, utilizador["tenant_id"], dados)

# ==========================================
# C. CONSULTAR O CONTRATO DE UMA MATRÍCULA
# ==========================================
@router.get("/matriculas/{matricula_id}/contrato")
async def obter_contrato_da_matricula(
    matricula_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Devolve o contrato financeiro já assinado desta matrícula (404 se ainda não existir)."""
    return await crud_financeiro.obter_contrato_da_matricula(db, utilizador["tenant_id"], matricula_id)

# ==========================================
# D. EXTRATO — TODAS AS PARCELAS DE UM CONTRATO
# ==========================================
@router.get("/contratos/{contrato_id}/faturas")
async def listar_faturas_do_contrato(
    contrato_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Extrato financeiro completo do ano letivo — usado no Histórico Financeiro."""
    return await crud_financeiro.listar_faturas_do_contrato(db, utilizador["tenant_id"], contrato_id)

# ==========================================
# E. DETALHE DE UMA FATURA (com juros/multa em tempo real)
# ==========================================
@router.get("/faturas/{fatura_id}")
async def obter_fatura(
    fatura_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_financeiro.obter_fatura(db, utilizador["tenant_id"], fatura_id)

# ==========================================
# F. MARCAR FATURA COMO PAGA (via manual — Secretaria)
# ==========================================
@router.patch("/faturas/{fatura_id}/marcar-pago")
async def marcar_fatura_paga(
    fatura_id: uuid.UUID,
    dados: FaturaMarcarPago,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    agendar_email = await _via_background_tasks(background_tasks)
    valor_pago = await crud_financeiro.marcar_fatura_paga(db, utilizador["tenant_id"], fatura_id, dados, agendar_email)
    return {"mensagem": "Fatura marcada como paga.", "valor_pago_realizado": valor_pago}

# ==========================================
# G1. GERAR/EMITIR COBRANÇA (PayPal)
# ==========================================
@router.post("/faturas/{fatura_id}/gerar-cobranca")
async def gerar_cobranca(
    fatura_id: uuid.UUID,
    dados: GerarCobrancaRequest,
    db: AsyncSession = Depends(obter_sessao_db),
    # Aberto a qualquer utilizador autenticado — o Portal do
    # Responsável, quando existir, vai chamar isto sem ser Gestor/Secretaria.
    utilizador: dict = Depends(obter_utilizador_atual)
):
    return await crud_financeiro.gerar_cobranca(db, utilizador["tenant_id"], fatura_id, dados)

# ==========================================
# G2. CAPTURAR PAGAMENTO (após o responsável aprovar no PayPal)
# ==========================================
@router.post("/transacoes/capturar")
async def capturar_pagamento(
    dados: CapturarPagamentoRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """
    Chamado pelo front-end assim que o PayPal redireciona de volta com
    sucesso (?paypal_retorno=sucesso&token=<order_id>). O Webhook
    (POST /api/v1/webhooks/paypal/pagamentos) faz o mesmo como rede de
    segurança caso o utilizador feche a janela antes disto correr.
    """
    agendar_email = await _via_background_tasks(background_tasks)
    status_pagamento = await crud_financeiro.capturar_pagamento(db, utilizador["tenant_id"], dados, agendar_email)
    mensagem = "Pagamento já tinha sido confirmado." if status_pagamento == "PAGO" else "Pagamento confirmado com sucesso."
    return {"mensagem": mensagem, "status": status_pagamento}

# ==========================================
# G. RÉGUA DE COBRANÇA (RN04)
# ==========================================
@router.post("/regua-cobranca/processar")
async def processar_regua_cobranca(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """
    Disparo manual da RN04 para a escola do utilizador — útil para
    testar/forçar já, mas o job diário em app/core/scheduler.py já
    corre isto automaticamente para todas as escolas, todos os dias.
    """
    agendar_email = await _via_background_tasks(background_tasks)
    contagem = await crud_financeiro.processar_regua_cobranca_do_tenant(db, utilizador["tenant_id"], agendar_email)
    return {"mensagem": "Régua de cobrança processada.", "emails_enviados": contagem}

# ==========================================
# WEBHOOK (RN03) — rota pública, chamada pelo PayPal
# ==========================================
@router_webhooks.post("/paypal/pagamentos")
async def webhook_paypal_pagamentos(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db_publica)
):
    """
    Rede de segurança do RN03: confirma o pagamento mesmo que o
    responsável tenha fechado a janela antes do redirecionamento de
    volta (POST /financeiro/transacoes/capturar) chegar a correr.
    Responde 200 sempre, para o PayPal não ficar a retentar indefinidamente.
    """
    corpo_bruto = await request.body()
    corpo_json = await request.json()
    agendar_email = await _via_background_tasks(background_tasks)
    await crud_financeiro.processar_webhook_paypal(db, dict(request.headers), corpo_bruto, corpo_json, agendar_email)
    return {"recebido": True}
