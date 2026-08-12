from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.session import obter_sessao_db
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.database.models_matricula import Matricula
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade
from app.core.security import obter_utilizador_atual, exigir_perfil
from app.core.email import enviar_email, template_base

router = APIRouter(prefix="/api/v1/financeiro", tags=["Financeiro"])

# Só Gestor/Secretaria criam/gerem contratos e mexem em pagamentos — o
# mesmo padrão RBAC usado em matrículas/académico. Leitura (extrato,
# detalhe da fatura) fica aberta a qualquer utilizador autenticado da
# escola (o Portal do Responsável/Aluno, quando existir, vai precisar
# de ler sem ser Gestor).
_PODE_GERIR = exigir_perfil("GESTOR", "SECRETARIA")

# RN02 do documento: juros diários e multa fixa aplicados on-the-fly,
# nunca gravados na base de dados por um job diário.
TAXA_JUROS_DIARIA = Decimal("0.00033")  # 0.033% ao dia
TAXA_MULTA_ATRASO = Decimal("0.02")     # 2% fixo, uma vez, ao entrar em atraso
DOIS_CASAS = Decimal("0.01")

STATUS_VALIDOS = {"PENDENTE", "PAGO", "CANCELADO", "NEGOCIADO"}


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class ContratoCreate(BaseModel):
    matricula_id: uuid.UUID
    responsavel_id: uuid.UUID
    valor_total_anual: Decimal
    quantidade_parcelas: int = 12
    dia_vencimento_padrao: int = 5
    percentual_desconto_bolsa: Decimal = Decimal("0.00")
    mes_primeira_parcela: int | None = None  # 1-12; default: mês seguinte a hoje


class FaturaMarcarPago(BaseModel):
    valor_pago: Decimal | None = None  # se omitido, assume o valor atualizado (com juros/multa, se houver)
    forma_pagamento: str = "MANUAL"


# ==========================================
# RN02 - CÁLCULO DE JUROS E MULTA (ON-THE-FLY)
# ==========================================
def _calcular_situacao_fatura(fatura: FaturaMensalidade) -> dict:
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


def _serializar_fatura(fatura: FaturaMensalidade) -> dict:
    situacao = _calcular_situacao_fatura(fatura)
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
    }


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
    tenant_id = utilizador["tenant_id"]
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
@router.post("/contratos", status_code=status.HTTP_201_CREATED)
async def criar_contrato(
    dados: ContratoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """
    Assina o contrato financeiro do ano letivo e gera de imediato todas
    as parcelas (Fatura_Mensalidade). O documento (RN01) prevê gerar as
    faturas em lote 15 dias antes do vencimento para não emitir
    cobranças no gateway antes da hora — como ainda não há gateway
    integrado (Transacao_Gateway fica para quando houver), gerar já as
    linhas de fatura não tem esse custo; é só a emissão da cobrança em
    si que ficaria condicionada a essa janela.
    """
    tenant_id = utilizador["tenant_id"]

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
@router.get("/matriculas/{matricula_id}/contrato")
async def obter_contrato_da_matricula(
    matricula_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Devolve o contrato financeiro já assinado desta matrícula (404 se ainda não existir)."""
    contrato = (await db.execute(
        select(ContratoFinanceiro).where(
            ContratoFinanceiro.matricula_id == matricula_id,
            ContratoFinanceiro.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Esta matrícula ainda não tem contrato financeiro.")
    return contrato


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
    tenant_id = utilizador["tenant_id"]
    contrato = (await db.execute(
        select(ContratoFinanceiro).where(ContratoFinanceiro.id == contrato_id, ContratoFinanceiro.tenant_id == tenant_id)
    )).scalars().first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato financeiro não encontrado na sua instituição.")

    faturas = (await db.execute(
        select(FaturaMensalidade)
        .where(FaturaMensalidade.contrato_id == contrato_id, FaturaMensalidade.tenant_id == tenant_id)
        .order_by(FaturaMensalidade.numero_parcela)
    )).scalars().all()

    return [_serializar_fatura(fatura) for fatura in faturas]


# ==========================================
# E. DETALHE DE UMA FATURA (com juros/multa em tempo real)
# ==========================================
@router.get("/faturas/{fatura_id}")
async def obter_fatura(
    fatura_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    fatura = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == fatura_id, FaturaMensalidade.tenant_id == utilizador["tenant_id"])
    )).scalars().first()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada na sua instituição.")
    return _serializar_fatura(fatura)


# ==========================================
# F. MARCAR FATURA COMO PAGA (substitui o webhook do gateway, por agora)
# ==========================================
@router.patch("/faturas/{fatura_id}/marcar-pago")
async def marcar_fatura_paga(
    fatura_id: uuid.UUID,
    dados: FaturaMarcarPago,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """
    Regista manualmente um pagamento recebido fora do sistema (dinheiro,
    transferência, MB Way, ...). Quando existir um gateway real
    (Transacao_Gateway + Webhook — RN03 do documento), esta mesma
    transição de estado passa a acontecer automaticamente; este
    endpoint fica como via manual de reconciliação para a Secretaria.
    """
    tenant_id = utilizador["tenant_id"]
    fatura = (await db.execute(
        select(FaturaMensalidade).where(FaturaMensalidade.id == fatura_id, FaturaMensalidade.tenant_id == tenant_id)
    )).scalars().first()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada na sua instituição.")
    if fatura.status_pagamento == "PAGO":
        raise HTTPException(status_code=400, detail="Esta fatura já está marcada como paga.")
    if fatura.status_pagamento == "CANCELADO":
        raise HTTPException(status_code=400, detail="Esta fatura está cancelada e não pode ser marcada como paga.")

    situacao = _calcular_situacao_fatura(fatura)
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
            background_tasks.add_task(
                enviar_email,
                destinatario=responsavel.email,
                assunto=f"Pagamento recebido — parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas}",
                corpo_html=template_base(
                    "Pagamento confirmado",
                    f"Recebemos o pagamento da parcela {fatura.numero_parcela}/{contrato.quantidade_parcelas}, "
                    f"no valor de {valor_pago}€. Obrigado!"
                )
            )

    return {"mensagem": "Fatura marcada como paga.", "valor_pago_realizado": valor_pago}


# ==========================================
# G. RÉGUA DE COBRANÇA (RN04) — disparo manual, por agora
# ==========================================
@router.post("/regua-cobranca/processar")
async def processar_regua_cobranca(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_GERIR)
):
    """
    RN04 do documento: 3 dias antes do vencimento, no dia do vencimento
    e 5 dias de atraso, o responsável recebe um e-mail. Sem um
    agendador (cron/Celery-beat) nesta fase, este endpoint faz o
    varrimento sob pedido do Gestor; a chamada é idempotente por
    fatura+etapa (marca *_enviado_em antes de reenviar).
    """
    tenant_id = utilizador["tenant_id"]
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
            background_tasks.add_task(
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
            background_tasks.add_task(
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
            situacao = _calcular_situacao_fatura(fatura)
            background_tasks.add_task(
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
    return {"mensagem": "Régua de cobrança processada.", "emails_enviados": contagem}
