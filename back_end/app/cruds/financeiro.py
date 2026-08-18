"""
Acesso a dados e regras de negócio (RN02, RN04) do Financeiro, incluindo
a integração com a PayPal Orders API (Transacao_Gateway).

O envio de e-mails e o despacho do webhook continuam desacoplados de
BackgroundTasks/Request do FastAPI através do parâmetro `agendar_email`
— o mesmo padrão usado em app/core/scheduler.py para o job diário (ver
processar_regua_cobranca_do_tenant): a rota decide *como* despachar
(BackgroundTasks.add_task no pedido HTTP, envio direto no scheduler),
este módulo só decide *quando*.
"""
import logging
import os
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.database.models_matricula import Matricula
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade, TransacaoGateway
from app.core.email import enviar_email, template_base
from app.core import paypal
from app.schemas.financeiro import CapturarPagamentoRequest, ContratoCreate, FaturaMarcarPago, GerarCobrancaRequest
from app.cruds.admin import esta_bloqueado_parcialmente

logger = logging.getLogger("financeiro")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

METODOS_GATEWAY_SUPORTADOS = {"PAYPAL"}

# RN02 do documento: juros diários e multa fixa aplicados on-the-fly,
# nunca gravados na base de dados por um job diário.
TAXA_JUROS_DIARIA = Decimal("0.00033")  # 0.033% ao dia
TAXA_MULTA_ATRASO = Decimal("0.02")     # 2% fixo, uma vez, ao entrar em atraso
DOIS_CASAS = Decimal("0.01")

STATUS_VALIDOS = {"PENDENTE", "PAGO", "CANCELADO", "NEGOCIADO"}


# ==========================================
# RN02 - CÁLCULO DE JUROS E MULTA (ON-THE-FLY)
# ==========================================
def calcular_situacao_fatura(fatura: FaturaMensalidade) -> dict:
    """
    Deriva o status "real" da fatura e o valor atualizado (com juros/multa)
    sem nunca escrever isto na base de dados — RN02 do documento. O
    status_pagamento gravado só muda quando alguém efetivamente paga,
    cancela ou negocia (ver marcar_fatura_paga).
    """
    hoje = date.today()

    if fatura.status_pagamento in ("PAGO", "CANCELADO", "NEGOCIADO"):
        return {
            "status_efetivo": fatura.status_pagamento,
            "valor_atualizado": fatura.valor_original,
            "juros_aplicados": Decimal("0.00"),
            "multa_aplicada": Decimal("0.00"),
            "dias_atraso": 0,
        }

    dias_atraso = (hoje - fatura.data_vencimento).days
    if dias_atraso <= 0:
        return {
            "status_efetivo": "PENDENTE",
            "valor_atualizado": fatura.valor_original,
            "juros_aplicados": Decimal("0.00"),
            "multa_aplicada": Decimal("0.00"),
            "dias_atraso": 0,
        }

    multa = (fatura.valor_original * TAXA_MULTA_ATRASO).quantize(DOIS_CASAS, rounding=ROUND_HALF_UP)
    juros = (fatura.valor_original * TAXA_JUROS_DIARIA * dias_atraso).quantize(DOIS_CASAS, rounding=ROUND_HALF_UP)
    return {
        "status_efetivo": "ATRASADO",
        "valor_atualizado": fatura.valor_original + multa + juros,
        "juros_aplicados": juros,
        "multa_aplicada": multa,
        "dias_atraso": dias_atraso,
    }


# ==========================================
# CONTROLO DE ACESSO DO PORTAL (RESPONSÁVEL/ALUNO)
# ==========================================
# GESTOR/SECRETARIA/PROFESSOR continuam a ver tudo da escola (como já
# acontecia antes do Portal existir) — as funções abaixo só restringem
# quando o utilizador autenticado é um login de RESPONSAVEL ou ALUNO,
# que só pode ler/pagar o que pertence aos seus próprios educandos.
async def _aluno_ids_permitidos_no_portal(db: AsyncSession, tenant_id, utilizador: dict) -> set[uuid.UUID] | None:
    """None = sem restrição. Devolve um set (possivelmente vazio) só para RESPONSAVEL/ALUNO."""
    perfil = utilizador.get("perfil_acesso")
    if perfil == "ALUNO":
        aluno_id = (await db.execute(
            select(Aluno.id).where(Aluno.usuario_id == utilizador["usuario_id"], Aluno.tenant_id == tenant_id)
        )).scalar_one_or_none()
        return {aluno_id} if aluno_id else set()
    if perfil == "RESPONSAVEL":
        responsavel_id = (await db.execute(
            select(ResponsavelFinanceiroLegal.id).where(
                ResponsavelFinanceiroLegal.usuario_id == utilizador["usuario_id"],
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
        if not responsavel_id:
            return set()
        ids = (await db.execute(
            select(AlunoResponsavel.aluno_id).where(AlunoResponsavel.responsavel_id == responsavel_id)
        )).scalars().all()
        return set(ids)
    return None


async def _garantir_acesso_via_matricula(db: AsyncSession, tenant_id, utilizador: dict, matricula_id: uuid.UUID) -> None:
    permitidos = await _aluno_ids_permitidos_no_portal(db, tenant_id, utilizador)
    if permitidos is None:
        return
    aluno_id = (await db.execute(
        select(Matricula.aluno_id).where(Matricula.id == matricula_id, Matricula.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if aluno_id is None or aluno_id not in permitidos:
        raise HTTPException(status_code=403, detail="Sem acesso a este aluno.")


async def _garantir_acesso_via_fatura(db: AsyncSession, tenant_id, utilizador: dict, fatura: FaturaMensalidade) -> None:
    contrato = (await db.execute(
        select(ContratoFinanceiro).where(ContratoFinanceiro.id == fatura.contrato_id, ContratoFinanceiro.tenant_id == tenant_id)
    )).scalars().first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato financeiro não encontrado na sua instituição.")
    await _garantir_acesso_via_matricula(db, tenant_id, utilizador, contrato.matricula_id)


def _serializar_transacao(transacao: TransacaoGateway) -> dict:
    return {
        "transacao_id": transacao.id,
        "metodo": transacao.metodo_pagamento,
        "order_id": transacao.gateway_transaction_id,
        "approve_url": transacao.dados_cobranca.get("approve_url"),
    }


def serializar_fatura(
    fatura: FaturaMensalidade, transacoes_ativas: list[TransacaoGateway] | None = None, pode_pagar: bool = True
) -> dict:
    situacao = calcular_situacao_fatura(fatura)
    return {
        "id": fatura.id,
        "contrato_id": fatura.contrato_id,
        "numero_parcela": fatura.numero_parcela,
        "valor_original": fatura.valor_original,
        "data_vencimento": fatura.data_vencimento,
        "status_pagamento": fatura.status_pagamento,
        "data_pagamento_realizado": fatura.data_pagamento_realizado,
        "valor_pago_realizado": fatura.valor_pago_realizado,
        "forma_pagamento": fatura.forma_pagamento,
        **situacao,
        "transacoes_ativas": [_serializar_transacao(t) for t in (transacoes_ativas or [])],
        # RN08: só se pode pagar/cobrar a parcela mais antiga ainda
        # pendente do contrato — nunca saltar parcelas. Para faturas já
        # resolvidas (PAGO/CANCELADO/NEGOCIADO) isto não se aplica.
        "pode_pagar": pode_pagar,
    }


async def _pode_pagar_fatura(db: AsyncSession, tenant_id, fatura: FaturaMensalidade) -> bool:
    """RN08: verdadeiro se não houver nenhuma parcela anterior (numero_parcela menor) do mesmo contrato ainda PENDENTE."""
    if fatura.status_pagamento != "PENDENTE":
        return True
    parcela_anterior_em_aberto = (await db.execute(
        select(FaturaMensalidade.id).where(
            FaturaMensalidade.contrato_id == fatura.contrato_id,
            FaturaMensalidade.numero_parcela < fatura.numero_parcela,
            FaturaMensalidade.status_pagamento == "PENDENTE"
        ).limit(1)
    )).scalar_one_or_none()
    return parcela_anterior_em_aberto is None


async def _garantir_ordem_parcela(db: AsyncSession, tenant_id, fatura: FaturaMensalidade) -> None:
    if not await _pode_pagar_fatura(db, tenant_id, fatura):
        raise HTTPException(
            status_code=400,
            detail=f"Só pode pagar/cobrar as parcelas em ordem — existe uma parcela anterior (antes da {fatura.numero_parcela}ª) ainda pendente."
        )


# ==========================================
# A. RESPONSÁVEIS ELEGÍVEIS (para o formulário de novo contrato)
# ==========================================
async def listar_responsaveis_da_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID) -> list[dict]:
    """Lista os responsáveis do aluno associado a esta matrícula, para escolher quem paga."""
    matricula = (await db.execute(
        select(Matricula).where(Matricula.id == matricula_id, Matricula.tenant_id == tenant_id)
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada na sua instituição.")

    resultado = await db.execute(
        select(ResponsavelFinanceiroLegal, AlunoResponsavel.tipo_parentesco, AlunoResponsavel.responsavel_financeiro)
        .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
        .where(AlunoResponsavel.aluno_id == matricula.aluno_id, ResponsavelFinanceiroLegal.tenant_id == tenant_id)
    )
    return [
        {
            "responsavel_id": responsavel.id,
            "nome_completo": responsavel.nome_completo,
            "email": responsavel.email,
            "tipo_parentesco": tipo_parentesco,
            "responsavel_financeiro": responsavel_financeiro,
        }
        for responsavel, tipo_parentesco, responsavel_financeiro in resultado.all()
    ]


# ==========================================
# B. CRIAR CONTRATO FINANCEIRO (E GERAR AS FATURAS)
# ==========================================
async def criar_contrato(db: AsyncSession, tenant_id, dados: ContratoCreate) -> ContratoFinanceiro:
    """
    Assina o contrato financeiro do ano letivo e gera de imediato todas
    as parcelas (Fatura_Mensalidade). O documento (RN01) prevê gerar as
    faturas em lote 15 dias antes do vencimento para não emitir
    cobranças no gateway antes da hora — como a linha de fatura em si
    não custa nada (só o pedido ao gateway, em gerar_cobranca), gerá-las
    já no ato da assinatura não tem esse custo.
    """
    # Sanção progressiva do Super Admin (licença vencida há 15+ dias) —
    # ver app/cruds/admin.py::esta_bloqueado_parcialmente.
    if await esta_bloqueado_parcialmente(db, tenant_id):
        raise HTTPException(
            status_code=403,
            detail="A licença desta escola está vencida há mais de 15 dias — novos contratos financeiros ficam bloqueados até regularizar a situação junto do Super Admin."
        )

    if dados.quantidade_parcelas < 1 or dados.quantidade_parcelas > 36:
        raise HTTPException(status_code=400, detail="Quantidade de parcelas deve estar entre 1 e 36.")
    if not (1 <= dados.dia_vencimento_padrao <= 28):
        raise HTTPException(status_code=400, detail="Dia de vencimento deve estar entre 1 e 28 (para existir em todos os meses).")
    if dados.valor_total_anual <= 0:
        raise HTTPException(status_code=400, detail="Valor total anual deve ser maior que zero.")
    if not (0 <= dados.percentual_desconto_bolsa <= 100):
        raise HTTPException(status_code=400, detail="Percentual de desconto de bolsa deve estar entre 0 e 100.")

    matricula = (await db.execute(
        select(Matricula).where(Matricula.id == dados.matricula_id, Matricula.tenant_id == tenant_id)
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada na sua instituição.")

    vinculo = (await db.execute(
        select(AlunoResponsavel).where(
            AlunoResponsavel.aluno_id == matricula.aluno_id,
            AlunoResponsavel.responsavel_id == dados.responsavel_id,
            AlunoResponsavel.tenant_id == tenant_id
        )
    )).scalars().first()
    if not vinculo:
        raise HTTPException(status_code=400, detail="Este responsável não está vinculado ao aluno desta matrícula.")

    valor_com_desconto = dados.valor_total_anual * (1 - dados.percentual_desconto_bolsa / 100)
    valor_parcela = (valor_com_desconto / dados.quantidade_parcelas).quantize(DOIS_CASAS, rounding=ROUND_HALF_UP)

    novo_contrato = ContratoFinanceiro(
        tenant_id=tenant_id,
        matricula_id=dados.matricula_id,
        responsavel_id=dados.responsavel_id,
        valor_total_anual=dados.valor_total_anual,
        quantidade_parcelas=dados.quantidade_parcelas,
        dia_vencimento_padrao=dados.dia_vencimento_padrao,
        percentual_desconto_bolsa=dados.percentual_desconto_bolsa,
    )
    db.add(novo_contrato)
    try:
        await db.flush()  # obter o id do contrato sem ainda fechar a transação
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um contrato financeiro para esta matrícula.")

    hoje = date.today()
    if dados.mes_primeira_parcela is not None:
        mes_inicial = dados.mes_primeira_parcela
        ano_inicial = hoje.year if mes_inicial >= hoje.month else hoje.year + 1
    elif hoje.month == 12:
        mes_inicial, ano_inicial = 1, hoje.year + 1
    else:
        mes_inicial, ano_inicial = hoje.month + 1, hoje.year

    mes, ano = mes_inicial, ano_inicial
    for numero in range(1, dados.quantidade_parcelas + 1):
        db.add(FaturaMensalidade(
            tenant_id=tenant_id,
            contrato_id=novo_contrato.id,
            numero_parcela=numero,
            valor_original=valor_parcela,
            data_vencimento=date(ano, mes, dados.dia_vencimento_padrao),
            status_pagamento="PENDENTE",
        ))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    await db.commit()
    await db.refresh(novo_contrato)
    return novo_contrato


# ==========================================
# C. CONSULTAR O CONTRATO DE UMA MATRÍCULA
# ==========================================
async def obter_contrato_da_matricula(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, utilizador: dict) -> ContratoFinanceiro:
    """Devolve o contrato financeiro já assinado desta matrícula (404 se ainda não existir)."""
    await _garantir_acesso_via_matricula(db, tenant_id, utilizador, matricula_id)

    contrato = (await db.execute(
        select(ContratoFinanceiro).where(
            ContratoFinanceiro.matricula_id == matricula_id,
            ContratoFinanceiro.tenant_id == tenant_id
        )
    )).scalars().first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Esta matrícula ainda não tem contrato financeiro.")
    return contrato


# ==========================================
# D. EXTRATO — TODAS AS PARCELAS DE UM CONTRATO
# ==========================================
async def listar_faturas_do_contrato(db: AsyncSession, tenant_id, contrato_id: uuid.UUID, utilizador: dict) -> list[dict]:
    """Extrato financeiro completo do ano letivo — usado no Histórico Financeiro."""
    contrato = (await db.execute(
        select(ContratoFinanceiro).where(ContratoFinanceiro.id == contrato_id, ContratoFinanceiro.tenant_id == tenant_id)
    )).scalars().first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato financeiro não encontrado na sua instituição.")
    await _garantir_acesso_via_matricula(db, tenant_id, utilizador, contrato.matricula_id)

    faturas = (await db.execute(
        select(FaturaMensalidade)
        .where(FaturaMensalidade.contrato_id == contrato_id, FaturaMensalidade.tenant_id == tenant_id)
        .order_by(FaturaMensalidade.numero_parcela)
    )).scalars().all()

    # Uma única query para as transações em aberto de todas as faturas
    # (em vez de N+1) — agrupadas por fatura_id em Python.
    transacoes = (await db.execute(
        select(TransacaoGateway).where(
            TransacaoGateway.fatura_id.in_([f.id for f in faturas]),
            TransacaoGateway.tenant_id == tenant_id,
            TransacaoGateway.status == "AGUARDANDO_PAGAMENTO"
        )
    )).scalars().all()
    transacoes_por_fatura: dict[uuid.UUID, list[TransacaoGateway]] = {}
    for t in transacoes:
        transacoes_por_fatura.setdefault(t.fatura_id, []).append(t)

    # RN08: dentro desta lista (já ordenada por numero_parcela) só a
    # primeira PENDENTE é pagável — não precisa de outra query por fatura.
    primeira_pendente_vista = False
    faturas_serializadas = []
    for fatura in faturas:
        if fatura.status_pagamento != "PENDENTE":
            pode_pagar = True
        elif not primeira_pendente_vista:
            pode_pagar = True
            primeira_pendente_vista = True
        else:
            pode_pagar = False
        faturas_serializadas.append(serializar_fatura(fatura, transacoes_por_fatura.get(fatura.id), pode_pagar))
    return faturas_serializadas


# ==========================================
# E. DETALHE DE UMA FATURA (com juros/multa em tempo real)
# ==========================================
async def obter_fatura(db: AsyncSession, tenant_id, fatura_id: uuid.UUID, utilizador: dict) -> dict:
    fatura = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == fatura_id, FaturaMensalidade.tenant_id == tenant_id)
    )).scalars().first()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada na sua instituição.")
    await _garantir_acesso_via_fatura(db, tenant_id, utilizador, fatura)

    transacoes_ativas = (await db.execute(
        select(TransacaoGateway).where(
            TransacaoGateway.fatura_id == fatura_id,
            TransacaoGateway.tenant_id == tenant_id,
            TransacaoGateway.status == "AGUARDANDO_PAGAMENTO"
        )
    )).scalars().all()

    pode_pagar = await _pode_pagar_fatura(db, tenant_id, fatura)
    return serializar_fatura(fatura, transacoes_ativas, pode_pagar)


# ==========================================
# F. MARCAR FATURA COMO PAGA (via manual — Secretaria)
# ==========================================
async def marcar_fatura_paga(db: AsyncSession, tenant_id, fatura_id: uuid.UUID, dados: FaturaMarcarPago, agendar_email) -> Decimal:
    """
    Regista manualmente um pagamento recebido fora do sistema (dinheiro,
    transferência, MB Way, ...). Para o PayPal, a mesma transição de
    estado acontece automaticamente via capturar_pagamento/webhook; este
    caminho fica como via manual de reconciliação para a Secretaria.
    Devolve o valor_pago_realizado.
    """
    fatura = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == fatura_id, FaturaMensalidade.tenant_id == tenant_id)
    )).scalars().first()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada na sua instituição.")
    if fatura.status_pagamento == "PAGO":
        raise HTTPException(status_code=400, detail="Esta fatura já está marcada como paga.")
    if fatura.status_pagamento == "CANCELADO":
        raise HTTPException(status_code=400, detail="Esta fatura está cancelada e não pode ser marcada como paga.")
    await _garantir_ordem_parcela(db, tenant_id, fatura)

    situacao = calcular_situacao_fatura(fatura)
    valor_pago = dados.valor_pago if dados.valor_pago is not None else situacao["valor_atualizado"]

    fatura.status_pagamento = "PAGO"
    fatura.data_pagamento_realizado = datetime.now(timezone.utc)
    fatura.valor_pago_realizado = valor_pago
    fatura.forma_pagamento = dados.forma_pagamento
    await db.commit()

    contrato = (await db.execute(
        select(ContratoFinanceiro).where(ContratoFinanceiro.id == fatura.contrato_id)
    )).scalars().first()
    if contrato:
        responsavel = (await db.execute(
            select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.id == contrato.responsavel_id)
        )).scalars().first()
        if responsavel and responsavel.email:
            await agendar_email(
                enviar_email,
                destinatario=responsavel.email,
                assunto=f"Pagamento recebido — parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas}",
                corpo_html=template_base(
                    "Pagamento confirmado",
                    f"Recebemos o pagamento da parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas}, "
                    f"no valor de {valor_pago}€. Obrigado!"
                )
            )

    return valor_pago


# ==========================================
# G1. GERAR/EMITIR COBRANÇA (PayPal)
# ==========================================
async def gerar_cobranca(db: AsyncSession, tenant_id, fatura_id: uuid.UUID, dados: GerarCobrancaRequest, utilizador: dict) -> dict:
    """
    Pede ao gateway (por agora só PayPal) os dados de pagamento de uma
    fatura. Idempotente: se já houver uma cobrança do mesmo método em
    aberto para esta fatura, devolve essa em vez de criar outra Order no
    PayPal (evita cobrar taxa de emissão em duplicado por duplo-clique).
    """
    if dados.metodo_pagamento not in METODOS_GATEWAY_SUPORTADOS:
        raise HTTPException(
            status_code=400,
            detail=f"Método de pagamento não suportado. Use um de: {', '.join(sorted(METODOS_GATEWAY_SUPORTADOS))}."
        )

    fatura = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == fatura_id, FaturaMensalidade.tenant_id == tenant_id)
    )).scalars().first()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada na sua instituição.")
    await _garantir_acesso_via_fatura(db, tenant_id, utilizador, fatura)
    if fatura.status_pagamento in ("PAGO", "CANCELADO"):
        raise HTTPException(status_code=400, detail="Esta fatura já está paga ou cancelada.")
    await _garantir_ordem_parcela(db, tenant_id, fatura)

    # Idempotência: reaproveita uma cobrança do mesmo método já em aberto.
    existente = (await db.execute(
        select(TransacaoGateway).where(
            TransacaoGateway.fatura_id == fatura_id,
            TransacaoGateway.tenant_id == tenant_id,
            TransacaoGateway.metodo_pagamento == dados.metodo_pagamento,
            TransacaoGateway.status == "AGUARDANDO_PAGAMENTO"
        )
    )).scalars().first()
    if existente:
        return {
            "transacao_id": existente.id,
            "fatura_id": fatura.id,
            "valor_cobrado": existente.dados_cobranca.get("valor"),
            "dados_pagamento": {"approve_url": existente.dados_cobranca.get("approve_url")},
            "status": existente.status,
        }

    situacao = calcular_situacao_fatura(fatura)
    valor_cobrado = situacao["valor_atualizado"]

    contrato = (await db.execute(
        select(ContratoFinanceiro).where(ContratoFinanceiro.id == fatura.contrato_id)
    )).scalars().first()
    aluno_nome = None
    aluno_id = None
    if contrato:
        linha_aluno = (await db.execute(
            select(Aluno.id, Aluno.nome_completo).join(Matricula, Matricula.aluno_id == Aluno.id)
            .where(Matricula.id == contrato.matricula_id)
        )).first()
        if linha_aluno:
            aluno_id, aluno_nome = linha_aluno

    # matricula_id (staff) ou aluno_id (Portal) vão na URL de retorno para
    # a página conseguir repor a seleção depois do PayPal redirecionar de
    # volta (o formulário fica "vazio" nesse ponto — é uma navegação nova).
    # Quem paga (Gestor/Secretaria vs. Responsável/Aluno) decide também
    # para que página do front-end o PayPal deve voltar.
    if utilizador.get("perfil_acesso") in ("ALUNO", "RESPONSAVEL"):
        pagina_retorno = "portal"
        sufixo_retorno = f"&aluno_id={aluno_id}" if aluno_id else ""
    else:
        pagina_retorno = "financeiro"
        matricula_id = contrato.matricula_id if contrato else None
        sufixo_retorno = f"&matricula_id={matricula_id}" if matricula_id else ""

    moeda = (await db.execute(select(Tenant.moeda).where(Tenant.id == tenant_id))).scalar_one_or_none() or "EUR"

    try:
        order = await paypal.criar_order(
            valor=str(valor_cobrado),
            referencia=str(fatura.id),
            descricao=f"Parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas if contrato else '?'} — {aluno_nome or ''}",
            return_url=f"{FRONTEND_URL}/{pagina_retorno}?paypal_retorno=sucesso{sufixo_retorno}",
            cancel_url=f"{FRONTEND_URL}/{pagina_retorno}?paypal_retorno=cancelado{sufixo_retorno}",
            moeda=moeda,
        )
    except paypal.PayPalNaoConfigurado as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Falha ao criar Order no PayPal para a fatura %s", fatura_id)
        raise HTTPException(status_code=502, detail="Não foi possível gerar a cobrança junto do PayPal. Tente novamente.")

    approve_url = next((link["href"] for link in order.get("links", []) if link.get("rel") == "approve"), None)

    nova_transacao = TransacaoGateway(
        tenant_id=tenant_id,
        fatura_id=fatura.id,
        metodo_pagamento="PAYPAL",
        gateway_transaction_id=order["id"],
        status="AGUARDANDO_PAGAMENTO",
        dados_cobranca={"approve_url": approve_url, "valor": str(valor_cobrado), "order_bruta": order},
    )
    db.add(nova_transacao)
    await db.commit()
    await db.refresh(nova_transacao)

    return {
        "transacao_id": nova_transacao.id,
        "fatura_id": fatura.id,
        "valor_cobrado": valor_cobrado,
        "dados_pagamento": {"approve_url": approve_url},
        "status": nova_transacao.status,
    }


# ==========================================
# G2. CAPTURAR PAGAMENTO (após o responsável aprovar no PayPal)
# ==========================================
async def capturar_pagamento(db: AsyncSession, tenant_id, dados: CapturarPagamentoRequest, agendar_email, utilizador: dict) -> str:
    """
    Chamado pelo front-end assim que o PayPal redireciona de volta com
    sucesso (?paypal_retorno=sucesso&token=<order_id>). Efetiva a
    cobrança (capture) e marca a fatura como PAGO. O Webhook
    (processar_webhook_paypal) faz a mesma coisa como rede de segurança
    caso o utilizador feche a janela antes disto correr. Devolve o status.
    """
    transacao = (await db.execute(
        select(TransacaoGateway).where(
            TransacaoGateway.gateway_transaction_id == dados.order_id,
            TransacaoGateway.tenant_id == tenant_id
        )
    )).scalars().first()
    if not transacao:
        raise HTTPException(status_code=404, detail="Transação não encontrada na sua instituição.")
    fatura_da_transacao = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == transacao.fatura_id, FaturaMensalidade.tenant_id == tenant_id)
    )).scalars().first()
    if fatura_da_transacao:
        await _garantir_acesso_via_fatura(db, tenant_id, utilizador, fatura_da_transacao)
    if transacao.status == "PAGO":
        return "PAGO"

    try:
        captura = await paypal.capturar_order(transacao.gateway_transaction_id)
    except Exception:
        logger.exception("Falha ao capturar a Order %s no PayPal", transacao.gateway_transaction_id)
        raise HTTPException(status_code=502, detail="Não foi possível confirmar o pagamento junto do PayPal.")

    if captura.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Pagamento não confirmado pelo PayPal (status: {captura.get('status')}).")

    await _efetivar_pagamento_gateway(db, transacao, captura, agendar_email)
    return "PAGO"


async def _efetivar_pagamento_gateway(db: AsyncSession, transacao: TransacaoGateway, captura: dict, agendar_email) -> None:
    """Passo comum entre a captura direta (front-end) e o webhook (RN03)."""
    fatura = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == transacao.fatura_id)
    )).scalars().first()
    if not fatura or fatura.status_pagamento == "PAGO":
        transacao.status = "PAGO"
        await db.commit()
        return

    try:
        valor_capturado = Decimal(
            captura["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]
        )
    except (KeyError, IndexError, TypeError):
        valor_capturado = transacao.dados_cobranca.get("valor")

    fatura.status_pagamento = "PAGO"
    fatura.data_pagamento_realizado = datetime.now(timezone.utc)
    fatura.valor_pago_realizado = valor_capturado
    fatura.forma_pagamento = "PAYPAL"

    transacao.status = "PAGO"
    transacao.dados_cobranca = {**transacao.dados_cobranca, "captura_bruta": captura}

    await db.commit()

    contrato = (await db.execute(
        select(ContratoFinanceiro).where(ContratoFinanceiro.id == fatura.contrato_id)
    )).scalars().first()
    if contrato:
        responsavel = (await db.execute(
            select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.id == contrato.responsavel_id)
        )).scalars().first()
        if responsavel and responsavel.email:
            await agendar_email(
                enviar_email,
                destinatario=responsavel.email,
                assunto=f"Pagamento recebido — parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas}",
                corpo_html=template_base(
                    "Pagamento confirmado",
                    f"Recebemos via PayPal o pagamento da parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas}, "
                    f"no valor de {valor_capturado}€. Obrigado!"
                )
            )


# ==========================================
# G. RÉGUA DE COBRANÇA (RN04)
# ==========================================
async def processar_regua_cobranca_do_tenant(db: AsyncSession, tenant_id, agendar_email) -> dict:
    """
    Núcleo da RN04, isolado do transporte HTTP para poder ser chamado
    tanto pelo endpoint manual (POST /regua-cobranca/processar, um
    tenant, com BackgroundTasks) como pelo scheduler diário
    (app/core/scheduler.py, todos os tenants ATIVOS, sem request/response
    à volta). `agendar_email` abstrai essa diferença: recebe
    (enviar_email, **kwargs) e decide como despachar — via
    BackgroundTasks.add_task no caso do endpoint, ou a enviar
    imediatamente no caso do scheduler.

    3 dias antes do vencimento, no dia do vencimento e 5 dias de
    atraso, o responsável recebe um e-mail; idempotente por
    fatura+etapa (marca *_enviado_em antes de reenviar).
    """
    hoje = date.today()

    faturas = (await db.execute(
        select(FaturaMensalidade, ContratoFinanceiro, Aluno.nome_completo, ResponsavelFinanceiroLegal.email)
        .join(ContratoFinanceiro, ContratoFinanceiro.id == FaturaMensalidade.contrato_id)
        .join(Matricula, Matricula.id == ContratoFinanceiro.matricula_id)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .join(ResponsavelFinanceiroLegal, ResponsavelFinanceiroLegal.id == ContratoFinanceiro.responsavel_id)
        .where(FaturaMensalidade.tenant_id == tenant_id, FaturaMensalidade.status_pagamento == "PENDENTE")
    )).all()

    contagem = {"lembrete_previo": 0, "lembrete_vencimento": 0, "aviso_atraso": 0}

    for fatura, contrato, nome_aluno, email_responsavel in faturas:
        if not email_responsavel:
            continue
        dias_para_vencer = (fatura.data_vencimento - hoje).days
        rotulo_parcela = f"{fatura.numero_parcela}/{contrato.quantidade_parcelas}"

        if dias_para_vencer == 3 and fatura.lembrete_previo_enviado_em is None:
            await agendar_email(
                enviar_email, destinatario=email_responsavel,
                assunto=f"Mensalidade de {nome_aluno} vence em breve",
                corpo_html=template_base(
                    "A sua mensalidade vence em breve",
                    f"A parcela {rotulo_parcela} de {nome_aluno}, no valor de {fatura.valor_original}€, "
                    f"vence em {fatura.data_vencimento.strftime('%d/%m/%Y')}."
                )
            )
            fatura.lembrete_previo_enviado_em = datetime.now(timezone.utc)
            contagem["lembrete_previo"] += 1

        elif dias_para_vencer == 0 and fatura.lembrete_vencimento_enviado_em is None:
            await agendar_email(
                enviar_email, destinatario=email_responsavel,
                assunto=f"Mensalidade de {nome_aluno} vence hoje",
                corpo_html=template_base(
                    "A sua mensalidade vence hoje",
                    f"A parcela {rotulo_parcela} de {nome_aluno}, no valor de {fatura.valor_original}€, vence hoje."
                )
            )
            fatura.lembrete_vencimento_enviado_em = datetime.now(timezone.utc)
            contagem["lembrete_vencimento"] += 1

        elif dias_para_vencer == -5 and fatura.aviso_atraso_enviado_em is None:
            situacao = calcular_situacao_fatura(fatura)
            await agendar_email(
                enviar_email, destinatario=email_responsavel,
                assunto=f"Mensalidade de {nome_aluno} em atraso",
                corpo_html=template_base(
                    "A sua mensalidade está em atraso",
                    f"A parcela {rotulo_parcela} de {nome_aluno} está em atraso há 5 dias. "
                    f"Valor atualizado (com juros e multa): {situacao['valor_atualizado']}€."
                )
            )
            fatura.aviso_atraso_enviado_em = datetime.now(timezone.utc)
            contagem["aviso_atraso"] += 1

    await db.commit()
    return contagem


# ==========================================
# WEBHOOK (RN03) — chamado pelo PayPal
# ==========================================
async def processar_webhook_paypal(db: AsyncSession, headers: dict, corpo_bruto: bytes, corpo_json: dict, agendar_email) -> None:
    """
    Rede de segurança do RN03: confirma o pagamento mesmo que o
    responsável tenha fechado a janela antes do redirecionamento de
    volta (capturar_pagamento) chegar a correr.

    Sem PAYPAL_WEBHOOK_ID configurado, a assinatura não é validada e o
    evento é ignorado (mas registado em log) — não confiamos em
    payloads não verificados que digam "paguei" sem confirmar que
    vieram mesmo do PayPal. Nunca levanta exceção — a rota deve
    responder 200 sempre, para o PayPal não ficar a retentar indefinidamente.
    """
    try:
        assinatura_valida = await paypal.verificar_assinatura_webhook(headers, corpo_bruto)
    except Exception:
        logger.exception("Erro ao verificar assinatura do webhook do PayPal.")
        return

    if not assinatura_valida:
        logger.warning("Webhook do PayPal recebido mas a assinatura não foi validada — ignorado.")
        return

    tipo_evento = corpo_json.get("event_type")
    if tipo_evento != "PAYMENT.CAPTURE.COMPLETED":
        return

    recurso = corpo_json.get("resource", {})
    order_id = (recurso.get("supplementary_data", {}) or {}).get("related_ids", {}).get("order_id")
    if not order_id:
        logger.warning("Webhook PAYMENT.CAPTURE.COMPLETED sem order_id em supplementary_data — ignorado.")
        return

    transacao = (await db.execute(
        select(TransacaoGateway).where(TransacaoGateway.gateway_transaction_id == order_id)
    )).scalars().first()
    if not transacao:
        logger.warning("Webhook do PayPal referencia a Order %s, que não existe na nossa base de dados.", order_id)
        return

    # A "captura" simulada aqui replica só o suficiente da resposta da
    # PayPal Orders API para _efetivar_pagamento_gateway conseguir ler o
    # valor pago; o resto do payload do evento fica em dados_cobranca.
    captura_simulada = {
        "purchase_units": [{"payments": {"captures": [{"amount": recurso.get("amount", {})}]}}]
    }
    await _efetivar_pagamento_gateway(db, transacao, captura_simulada, agendar_email)
