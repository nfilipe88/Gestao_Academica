"""
Acesso a dados e regras de negócio das Solicitações de Documentos —
ver app/database/models_documentos.py para a distinção entre as duas
direções (emissão pela escola vs. pedido da escola a terceiros).
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_academico import Disciplina, Turma
from app.database.models_diario import RegistroNota
from app.database.models_documentos import PrecoDocumento, SolicitacaoDocumentoEmissao, SolicitacaoDocumentoEscola
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, Professor, ResponsavelFinanceiroLegal
from app.core import documentos_pdf, paypal
from app.core.paginacao import paginar, paginar_linhas
from app.cruds import alunos as crud_alunos
from app.cruds import notificacoes as crud_notificacoes
from app.schemas.documentos import (
    EntregarFisicoRequest, PrecoDocumentoUpdate, ResponderSolicitacaoEscolaRequest,
    SolicitacaoDocumentoEmissaoCreate, SolicitacaoDocumentoEscolaCreate,
)

load_dotenv()
logger = logging.getLogger("documentos")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

TIPOS_DOCUMENTO = {"CERTIFICADO", "DECLARACAO", "HISTORICO_ESCOLAR", "BOLETIM", "OUTRO"}
FORMATOS_ENTREGA = {"DIGITAL", "FISICA"}
NOMES_TIPO_DOCUMENTO = {
    "CERTIFICADO": "Certificado de Frequência",
    "DECLARACAO": "Declaração",
    "HISTORICO_ESCOLAR": "Histórico Escolar",
    "BOLETIM": "Boletim de Notas",
    "OUTRO": "Outro documento",
}
DESTINATARIOS_ESCOLA_VALIDOS = {"ALUNO", "RESPONSAVEL", "PROFESSOR"}


# ==========================================
# A. TABELA DE PREÇOS (Gestor)
# ==========================================
async def listar_precos(db: AsyncSession, tenant_id) -> list[dict]:
    """Devolve os 5 tipos de documento sempre, com o preço 0/inativo se o Gestor ainda não configurou."""
    existentes = {
        p.tipo_documento: p
        for p in (await db.execute(select(PrecoDocumento).where(PrecoDocumento.tenant_id == tenant_id))).scalars().all()
    }
    return [
        {
            "tipo_documento": tipo,
            "nome": NOMES_TIPO_DOCUMENTO[tipo],
            "preco": existentes[tipo].preco if tipo in existentes else Decimal("0.00"),
            "ativo": existentes[tipo].ativo if tipo in existentes else False,
        }
        for tipo in sorted(TIPOS_DOCUMENTO)
    ]


async def atualizar_preco(db: AsyncSession, tenant_id, tipo_documento: str, dados: PrecoDocumentoUpdate) -> dict:
    if tipo_documento not in TIPOS_DOCUMENTO:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido. Use um de: {', '.join(sorted(TIPOS_DOCUMENTO))}.")
    if dados.preco < 0:
        raise HTTPException(status_code=400, detail="O preço não pode ser negativo.")

    preco = (await db.execute(
        select(PrecoDocumento).where(PrecoDocumento.tenant_id == tenant_id, PrecoDocumento.tipo_documento == tipo_documento)
    )).scalars().first()
    if preco:
        preco.preco = dados.preco
        preco.ativo = dados.ativo
    else:
        preco = PrecoDocumento(tenant_id=tenant_id, tipo_documento=tipo_documento, preco=dados.preco, ativo=dados.ativo)
        db.add(preco)
    await db.commit()
    return {"tipo_documento": tipo_documento, "nome": NOMES_TIPO_DOCUMENTO[tipo_documento], "preco": preco.preco, "ativo": preco.ativo}


# ==========================================
# B. PEDIDO DE EMISSÃO (Aluno/Responsável -> Escola)
# ==========================================
def _serializar_emissao(solicitacao: SolicitacaoDocumentoEmissao, aluno_nome: str | None = None) -> dict:
    return {
        "id": solicitacao.id,
        "aluno_id": solicitacao.aluno_id,
        "aluno_nome": aluno_nome,
        "tipo_documento": solicitacao.tipo_documento,
        "nome_tipo_documento": NOMES_TIPO_DOCUMENTO.get(solicitacao.tipo_documento, solicitacao.tipo_documento),
        "descricao_outro": solicitacao.descricao_outro,
        "formato_entrega": solicitacao.formato_entrega,
        "preco": solicitacao.preco,
        "status": solicitacao.status,
        "observacoes_escola": solicitacao.observacoes_escola,
        "data_solicitacao": solicitacao.data_solicitacao,
        "data_pagamento": solicitacao.data_pagamento,
        "data_conclusao": solicitacao.data_conclusao,
    }


async def criar_solicitacao_emissao(db: AsyncSession, tenant_id, utilizador: dict, dados: SolicitacaoDocumentoEmissaoCreate) -> dict:
    if dados.tipo_documento not in TIPOS_DOCUMENTO:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido. Use um de: {', '.join(sorted(TIPOS_DOCUMENTO))}.")
    if dados.formato_entrega not in FORMATOS_ENTREGA:
        raise HTTPException(status_code=400, detail=f"Formato de entrega inválido. Use um de: {', '.join(sorted(FORMATOS_ENTREGA))}.")
    if dados.tipo_documento == "OUTRO" and not (dados.descricao_outro and dados.descricao_outro.strip()):
        raise HTTPException(status_code=400, detail="Descreva o documento pretendido.")

    # Resolve para que aluno_id é o pedido: o próprio (ALUNO) ou, no caso
    # de RESPONSAVEL, o educando indicado (obrigatório se tiver mais de um).
    meus_alunos = await crud_alunos.resolver_meus_alunos(db, tenant_id, utilizador)
    if not meus_alunos:
        raise HTTPException(status_code=403, detail="Utilizador sem aluno associado.")
    if dados.aluno_id:
        if dados.aluno_id not in meus_alunos:
            raise HTTPException(status_code=403, detail="Sem acesso a este aluno.")
        aluno_id = dados.aluno_id
    elif len(meus_alunos) == 1:
        aluno_id = meus_alunos[0]
    else:
        raise HTTPException(status_code=400, detail="Indique para qual educando é o pedido (aluno_id).")

    preco_config = (await db.execute(
        select(PrecoDocumento).where(
            PrecoDocumento.tenant_id == tenant_id, PrecoDocumento.tipo_documento == dados.tipo_documento
        )
    )).scalars().first()
    if not preco_config or not preco_config.ativo:
        raise HTTPException(status_code=400, detail="Este tipo de documento não está disponível para pedido nesta instituição.")

    nova = SolicitacaoDocumentoEmissao(
        tenant_id=tenant_id,
        aluno_id=aluno_id,
        solicitante_usuario_id=utilizador["usuario_id"],
        tipo_documento=dados.tipo_documento,
        descricao_outro=dados.descricao_outro,
        formato_entrega=dados.formato_entrega,
        preco=preco_config.preco,
        status="PENDENTE_PAGAMENTO",
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return _serializar_emissao(nova)


async def _obter_solicitacao_emissao(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID) -> SolicitacaoDocumentoEmissao:
    solicitacao = (await db.execute(
        select(SolicitacaoDocumentoEmissao).where(
            SolicitacaoDocumentoEmissao.id == solicitacao_id, SolicitacaoDocumentoEmissao.tenant_id == tenant_id
        )
    )).scalars().first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada na sua instituição.")
    return solicitacao


async def _garantir_acesso_emissao(db: AsyncSession, tenant_id, utilizador: dict, solicitacao: SolicitacaoDocumentoEmissao) -> None:
    """Staff vê tudo; ALUNO/RESPONSAVEL só as solicitações dos seus próprios educandos."""
    if utilizador.get("perfil_acesso") in ("GESTOR", "SECRETARIA"):
        return
    await crud_alunos.garantir_aluno_permitido(db, tenant_id, utilizador, solicitacao.aluno_id)


async def listar_minhas_solicitacoes_emissao(db: AsyncSession, tenant_id, utilizador: dict) -> list[dict]:
    aluno_ids = await crud_alunos.resolver_meus_alunos(db, tenant_id, utilizador)
    if not aluno_ids:
        return []
    resultado = (await db.execute(
        select(SolicitacaoDocumentoEmissao, Aluno.nome_completo)
        .join(Aluno, Aluno.id == SolicitacaoDocumentoEmissao.aluno_id)
        .where(SolicitacaoDocumentoEmissao.tenant_id == tenant_id, SolicitacaoDocumentoEmissao.aluno_id.in_(aluno_ids))
        .order_by(SolicitacaoDocumentoEmissao.data_solicitacao.desc())
    )).all()
    return [_serializar_emissao(s, nome) for s, nome in resultado]


async def listar_solicitacoes_emissao_staff(db: AsyncSession, tenant_id, page: int, page_size: int) -> dict:
    query = (
        select(SolicitacaoDocumentoEmissao, Aluno.nome_completo)
        .join(Aluno, Aluno.id == SolicitacaoDocumentoEmissao.aluno_id)
        .where(SolicitacaoDocumentoEmissao.tenant_id == tenant_id)
        .order_by(SolicitacaoDocumentoEmissao.data_solicitacao.desc())
    )
    pagina = await paginar_linhas(db, query, page, page_size)
    pagina["items"] = [_serializar_emissao(s, nome) for s, nome in pagina["items"]]
    return pagina


async def gerar_cobranca_documento(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID, utilizador: dict) -> dict:
    solicitacao = await _obter_solicitacao_emissao(db, tenant_id, solicitacao_id)
    await _garantir_acesso_emissao(db, tenant_id, utilizador, solicitacao)
    if solicitacao.status != "PENDENTE_PAGAMENTO":
        raise HTTPException(status_code=400, detail="Esta solicitação já não está pendente de pagamento.")

    aluno = (await db.execute(select(Aluno).where(Aluno.id == solicitacao.aluno_id))).scalars().first()

    try:
        order = await paypal.criar_order(
            valor=str(solicitacao.preco),
            referencia=str(solicitacao.id),
            descricao=f"{NOMES_TIPO_DOCUMENTO.get(solicitacao.tipo_documento, solicitacao.tipo_documento)} — {aluno.nome_completo if aluno else ''}",
            return_url=f"{FRONTEND_URL}/portal?paypal_retorno=sucesso&aluno_id={solicitacao.aluno_id}&tab=documentos",
            cancel_url=f"{FRONTEND_URL}/portal?paypal_retorno=cancelado&aluno_id={solicitacao.aluno_id}&tab=documentos",
        )
    except paypal.PayPalNaoConfigurado as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Falha ao criar Order no PayPal para a solicitação de documento %s", solicitacao_id)
        raise HTTPException(status_code=502, detail="Não foi possível gerar a cobrança junto do PayPal. Tente novamente.")

    approve_url = next((link["href"] for link in order.get("links", []) if link.get("rel") == "approve"), None)
    solicitacao.paypal_order_id = order["id"]
    await db.commit()

    return {"solicitacao_id": solicitacao.id, "valor_cobrado": solicitacao.preco, "dados_pagamento": {"approve_url": approve_url}}


async def capturar_pagamento_documento(db: AsyncSession, tenant_id, order_id: str, utilizador: dict) -> dict:
    solicitacao = (await db.execute(
        select(SolicitacaoDocumentoEmissao).where(
            SolicitacaoDocumentoEmissao.paypal_order_id == order_id, SolicitacaoDocumentoEmissao.tenant_id == tenant_id
        )
    )).scalars().first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada na sua instituição.")
    await _garantir_acesso_emissao(db, tenant_id, utilizador, solicitacao)

    if solicitacao.status != "PENDENTE_PAGAMENTO":
        return _serializar_emissao(solicitacao)

    try:
        captura = await paypal.capturar_order(order_id)
    except Exception:
        logger.exception("Falha ao capturar a Order %s no PayPal (documento)", order_id)
        raise HTTPException(status_code=502, detail="Não foi possível confirmar o pagamento junto do PayPal.")

    if captura.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="O pagamento não foi concluído no PayPal.")

    solicitacao.status = "PAGO"
    solicitacao.data_pagamento = datetime.now(timezone.utc)
    await db.commit()

    aluno = (await db.execute(select(Aluno).where(Aluno.id == solicitacao.aluno_id))).scalars().first()
    if aluno and aluno.usuario_id:
        mensagem = (
            f"O pagamento do seu pedido de {NOMES_TIPO_DOCUMENTO.get(solicitacao.tipo_documento, solicitacao.tipo_documento)} "
            f"foi confirmado. {'Já pode fazer o download.' if solicitacao.formato_entrega == 'DIGITAL' else 'A escola vai preparar o documento para levantamento.'}"
        )
        await crud_notificacoes.criar_notificacao(
            db, tenant_id, aluno.usuario_id, tipo="SOLICITACAO_DOCUMENTO",
            titulo="Pagamento confirmado", mensagem=mensagem, link="/documentos"
        )

    return _serializar_emissao(solicitacao)


async def _construir_contexto_pdf(db: AsyncSession, tenant_id, solicitacao: SolicitacaoDocumentoEmissao) -> tuple[dict, dict]:
    aluno = (await db.execute(select(Aluno).where(Aluno.id == solicitacao.aluno_id, Aluno.tenant_id == tenant_id))).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    escola = {"nome": tenant.nome_fantasia if tenant else "", "razao_social": tenant.razao_social if tenant else "", "nif": tenant.nif if tenant else ""}

    if solicitacao.tipo_documento in ("CERTIFICADO", "DECLARACAO"):
        matricula_atual = (await db.execute(
            select(Matricula).where(Matricula.aluno_id == aluno.id, Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO")
            .order_by(Matricula.ano_letivo.desc())
        )).scalars().first()
        turma_nome = None
        if matricula_atual:
            turma_nome = (await db.execute(select(Turma.nome_codigo).where(Turma.id == matricula_atual.turma_id))).scalar_one_or_none()
        contexto = {
            "aluno_nome": aluno.nome_completo, "numero_documento": aluno.numero_documento,
            "turma_nome": turma_nome, "ano_letivo": matricula_atual.ano_letivo if matricula_atual else None,
        }

    elif solicitacao.tipo_documento == "BOLETIM":
        matricula_atual = (await db.execute(
            select(Matricula).where(Matricula.aluno_id == aluno.id, Matricula.tenant_id == tenant_id)
            .order_by(Matricula.status_matricula.desc(), Matricula.ano_letivo.desc())
        )).scalars().first()
        turma_nome, notas = None, []
        if matricula_atual:
            turma_nome = (await db.execute(select(Turma.nome_codigo).where(Turma.id == matricula_atual.turma_id))).scalar_one_or_none()
            linhas = (await db.execute(
                select(RegistroNota, Disciplina.nome)
                .join(Disciplina, Disciplina.id == RegistroNota.disciplina_id)
                .where(RegistroNota.matricula_id == matricula_atual.id, RegistroNota.tenant_id == tenant_id)
                .order_by(Disciplina.nome, RegistroNota.periodo_avaliacao)
            )).all()
            notas = [{"disciplina": nome, "periodo": nota.periodo_avaliacao, "tipo": nota.tipo_avaliacao, "valor": nota.valor_nota} for nota, nome in linhas]
        contexto = {
            "aluno_nome": aluno.nome_completo, "turma_nome": turma_nome,
            "ano_letivo": matricula_atual.ano_letivo if matricula_atual else None, "notas": notas,
        }

    elif solicitacao.tipo_documento == "HISTORICO_ESCOLAR":
        matriculas = (await db.execute(
            select(Matricula).where(Matricula.aluno_id == aluno.id, Matricula.tenant_id == tenant_id).order_by(Matricula.ano_letivo)
        )).scalars().all()
        anos = []
        for matricula in matriculas:
            turma_nome = (await db.execute(select(Turma.nome_codigo).where(Turma.id == matricula.turma_id))).scalar_one_or_none()
            linhas = (await db.execute(
                select(RegistroNota, Disciplina.nome)
                .join(Disciplina, Disciplina.id == RegistroNota.disciplina_id)
                .where(RegistroNota.matricula_id == matricula.id, RegistroNota.tenant_id == tenant_id)
                .order_by(Disciplina.nome, RegistroNota.periodo_avaliacao)
            )).all()
            anos.append({
                "ano_letivo": matricula.ano_letivo, "turma_nome": turma_nome, "status_matricula": matricula.status_matricula,
                "notas": [{"disciplina": nome, "periodo": nota.periodo_avaliacao, "valor": nota.valor_nota} for nota, nome in linhas],
            })
        contexto = {"aluno_nome": aluno.nome_completo, "numero_documento": aluno.numero_documento, "data_nascimento": aluno.data_nascimento, "anos": anos}

    else:  # OUTRO
        contexto = {"aluno_nome": aluno.nome_completo, "descricao": solicitacao.descricao_outro or "—"}

    return escola, contexto


async def gerar_pdf_solicitacao(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID, utilizador: dict) -> bytes:
    solicitacao = await _obter_solicitacao_emissao(db, tenant_id, solicitacao_id)
    await _garantir_acesso_emissao(db, tenant_id, utilizador, solicitacao)
    if solicitacao.status not in ("PAGO", "ENTREGUE"):
        raise HTTPException(status_code=400, detail="O documento só pode ser gerado depois de confirmado o pagamento.")

    escola, contexto = await _construir_contexto_pdf(db, tenant_id, solicitacao)
    pdf_bytes = documentos_pdf.gerar_pdf_documento(solicitacao.tipo_documento, escola, contexto)

    # Download digital pelo próprio aluno/responsável marca a entrega como
    # concluída automaticamente; staff a gerar para imprimir (formato
    # FISICA) não conta como entregue — isso só acontece em marcar_entrega_fisica.
    if solicitacao.status == "PAGO" and solicitacao.formato_entrega == "DIGITAL" and utilizador.get("perfil_acesso") in ("ALUNO", "RESPONSAVEL"):
        solicitacao.status = "ENTREGUE"
        solicitacao.data_conclusao = datetime.now(timezone.utc)
        await db.commit()

    return pdf_bytes


async def marcar_entrega_fisica(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID, dados: EntregarFisicoRequest) -> dict:
    solicitacao = await _obter_solicitacao_emissao(db, tenant_id, solicitacao_id)
    if solicitacao.status != "PAGO":
        raise HTTPException(status_code=400, detail="Só é possível marcar como entregue uma solicitação paga.")
    if solicitacao.formato_entrega != "FISICA":
        raise HTTPException(status_code=400, detail="Esta solicitação não é de entrega física.")

    solicitacao.status = "ENTREGUE"
    solicitacao.observacoes_escola = dados.observacoes
    solicitacao.data_conclusao = datetime.now(timezone.utc)
    await db.commit()

    aluno = (await db.execute(select(Aluno).where(Aluno.id == solicitacao.aluno_id))).scalars().first()
    if aluno and aluno.usuario_id:
        await crud_notificacoes.criar_notificacao(
            db, tenant_id, aluno.usuario_id, tipo="SOLICITACAO_DOCUMENTO",
            titulo="Documento pronto para levantamento",
            mensagem=f"O seu {NOMES_TIPO_DOCUMENTO.get(solicitacao.tipo_documento, solicitacao.tipo_documento)} já pode ser levantado na secretaria.",
            link="/documentos"
        )
    return _serializar_emissao(solicitacao)


async def cancelar_solicitacao_emissao(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID) -> dict:
    solicitacao = await _obter_solicitacao_emissao(db, tenant_id, solicitacao_id)
    if solicitacao.status in ("ENTREGUE", "CANCELADO"):
        raise HTTPException(status_code=400, detail="Esta solicitação já não pode ser cancelada.")
    solicitacao.status = "CANCELADO"
    await db.commit()
    return _serializar_emissao(solicitacao)


# ==========================================
# C. PEDIDO DA ESCOLA (Escola -> Aluno/Responsável/Professor)
# ==========================================
async def _resolver_destinatario_escola(db: AsyncSession, tenant_id, destinatario_tipo: str, destinatario_id: uuid.UUID) -> tuple[dict, uuid.UUID | None, str]:
    """Devolve (colunas FK a preencher, usuario_id p/ notificar, nome do destinatário)."""
    if destinatario_tipo == "ALUNO":
        aluno = (await db.execute(select(Aluno).where(Aluno.id == destinatario_id, Aluno.tenant_id == tenant_id))).scalars().first()
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")
        return {"destinatario_aluno_id": aluno.id}, aluno.usuario_id, aluno.nome_completo

    if destinatario_tipo == "RESPONSAVEL":
        responsavel = (await db.execute(
            select(ResponsavelFinanceiroLegal).where(ResponsavelFinanceiroLegal.id == destinatario_id, ResponsavelFinanceiroLegal.tenant_id == tenant_id)
        )).scalars().first()
        if not responsavel:
            raise HTTPException(status_code=404, detail="Responsável não encontrado na sua instituição.")
        return {"destinatario_responsavel_id": responsavel.id}, responsavel.usuario_id, responsavel.nome_completo

    if destinatario_tipo == "PROFESSOR":
        resultado = (await db.execute(
            select(Professor, Usuario.nome_completo).join(Usuario, Usuario.id == Professor.usuario_id)
            .where(Professor.id == destinatario_id, Professor.tenant_id == tenant_id)
        )).first()
        if not resultado:
            raise HTTPException(status_code=404, detail="Professor não encontrado na sua instituição.")
        professor, nome = resultado
        return {"destinatario_professor_id": professor.id}, professor.usuario_id, nome

    raise HTTPException(status_code=400, detail=f"Tipo de destinatário inválido. Use um de: {', '.join(sorted(DESTINATARIOS_ESCOLA_VALIDOS))}.")


def _serializar_escola(solicitacao: SolicitacaoDocumentoEscola, destinatario_nome: str | None = None, solicitante_nome: str | None = None) -> dict:
    return {
        "id": solicitacao.id,
        "destinatario_tipo": solicitacao.destinatario_tipo,
        "destinatario_nome": destinatario_nome,
        "destinatario_aluno_id": solicitacao.destinatario_aluno_id,
        "destinatario_responsavel_id": solicitacao.destinatario_responsavel_id,
        "destinatario_professor_id": solicitacao.destinatario_professor_id,
        "solicitante_nome": solicitante_nome,
        "titulo": solicitacao.titulo,
        "descricao": solicitacao.descricao,
        "status": solicitacao.status,
        "resposta_texto": solicitacao.resposta_texto,
        "respondido_em": solicitacao.respondido_em,
        "data_solicitacao": solicitacao.data_solicitacao,
    }


async def criar_solicitacao_escola(db: AsyncSession, tenant_id, utilizador: dict, dados: SolicitacaoDocumentoEscolaCreate) -> dict:
    if dados.destinatario_tipo not in DESTINATARIOS_ESCOLA_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo de destinatário inválido. Use um de: {', '.join(sorted(DESTINATARIOS_ESCOLA_VALIDOS))}.")

    colunas_fk, usuario_id_destinatario, nome_destinatario = await _resolver_destinatario_escola(db, tenant_id, dados.destinatario_tipo, dados.destinatario_id)

    nova = SolicitacaoDocumentoEscola(
        tenant_id=tenant_id,
        destinatario_tipo=dados.destinatario_tipo,
        solicitado_por_usuario_id=utilizador["usuario_id"],
        titulo=dados.titulo,
        descricao=dados.descricao,
        status="PENDENTE",
        **colunas_fk,
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)

    if usuario_id_destinatario:
        await crud_notificacoes.criar_notificacao(
            db, tenant_id, usuario_id_destinatario, tipo="SOLICITACAO_DOCUMENTO",
            titulo=f"A escola pediu: {dados.titulo}", mensagem=dados.descricao[:280], link="/documentos"
        )

    return _serializar_escola(nova, destinatario_nome=nome_destinatario)


async def _obter_solicitacao_escola(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID) -> SolicitacaoDocumentoEscola:
    solicitacao = (await db.execute(
        select(SolicitacaoDocumentoEscola).where(SolicitacaoDocumentoEscola.id == solicitacao_id, SolicitacaoDocumentoEscola.tenant_id == tenant_id)
    )).scalars().first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada na sua instituição.")
    return solicitacao


async def listar_solicitacoes_escola_staff(db: AsyncSession, tenant_id, page: int, page_size: int) -> dict:
    query = select(SolicitacaoDocumentoEscola).where(SolicitacaoDocumentoEscola.tenant_id == tenant_id).order_by(SolicitacaoDocumentoEscola.data_solicitacao.desc())
    pagina = await paginar(db, query, page, page_size)

    resultado = []
    for solicitacao in pagina["items"]:
        nome = None
        if solicitacao.destinatario_aluno_id:
            nome = (await db.execute(select(Aluno.nome_completo).where(Aluno.id == solicitacao.destinatario_aluno_id))).scalar_one_or_none()
        elif solicitacao.destinatario_responsavel_id:
            nome = (await db.execute(select(ResponsavelFinanceiroLegal.nome_completo).where(ResponsavelFinanceiroLegal.id == solicitacao.destinatario_responsavel_id))).scalar_one_or_none()
        elif solicitacao.destinatario_professor_id:
            nome = (await db.execute(
                select(Usuario.nome_completo).join(Professor, Professor.usuario_id == Usuario.id).where(Professor.id == solicitacao.destinatario_professor_id)
            )).scalar_one_or_none()
        resultado.append(_serializar_escola(solicitacao, destinatario_nome=nome))
    pagina["items"] = resultado
    return pagina


async def _resolver_meu_destinatario_id(db: AsyncSession, tenant_id, utilizador: dict) -> tuple[str, uuid.UUID] | None:
    """Para o próprio ALUNO/RESPONSAVEL/PROFESSOR: a que coluna destinatario_* ele corresponde."""
    perfil = utilizador.get("perfil_acesso")
    if perfil == "ALUNO":
        aluno_id = (await db.execute(select(Aluno.id).where(Aluno.usuario_id == utilizador["usuario_id"], Aluno.tenant_id == tenant_id))).scalar_one_or_none()
        return ("ALUNO", aluno_id) if aluno_id else None
    if perfil == "RESPONSAVEL":
        responsavel_id = (await db.execute(
            select(ResponsavelFinanceiroLegal.id).where(ResponsavelFinanceiroLegal.usuario_id == utilizador["usuario_id"], ResponsavelFinanceiroLegal.tenant_id == tenant_id)
        )).scalar_one_or_none()
        return ("RESPONSAVEL", responsavel_id) if responsavel_id else None
    if perfil == "PROFESSOR":
        professor_id = (await db.execute(
            select(Professor.id).where(Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == tenant_id)
        )).scalar_one_or_none()
        return ("PROFESSOR", professor_id) if professor_id else None
    return None


async def listar_minhas_solicitacoes_escola(db: AsyncSession, tenant_id, utilizador: dict) -> list[dict]:
    alvo = await _resolver_meu_destinatario_id(db, tenant_id, utilizador)
    if not alvo:
        return []
    tipo, meu_id = alvo
    coluna = {"ALUNO": SolicitacaoDocumentoEscola.destinatario_aluno_id, "RESPONSAVEL": SolicitacaoDocumentoEscola.destinatario_responsavel_id, "PROFESSOR": SolicitacaoDocumentoEscola.destinatario_professor_id}[tipo]

    solicitacoes = (await db.execute(
        select(SolicitacaoDocumentoEscola).where(SolicitacaoDocumentoEscola.tenant_id == tenant_id, coluna == meu_id)
        .order_by(SolicitacaoDocumentoEscola.data_solicitacao.desc())
    )).scalars().all()
    return [_serializar_escola(s) for s in solicitacoes]


async def responder_solicitacao_escola(db: AsyncSession, tenant_id, utilizador: dict, solicitacao_id: uuid.UUID, dados: ResponderSolicitacaoEscolaRequest) -> dict:
    solicitacao = await _obter_solicitacao_escola(db, tenant_id, solicitacao_id)

    alvo = await _resolver_meu_destinatario_id(db, tenant_id, utilizador)
    if not alvo:
        raise HTTPException(status_code=403, detail="Sem acesso a esta solicitação.")
    tipo, meu_id = alvo
    coluna_esperada = {"ALUNO": solicitacao.destinatario_aluno_id, "RESPONSAVEL": solicitacao.destinatario_responsavel_id, "PROFESSOR": solicitacao.destinatario_professor_id}[tipo]
    if coluna_esperada != meu_id:
        raise HTTPException(status_code=403, detail="Sem acesso a esta solicitação.")

    if solicitacao.status != "PENDENTE":
        raise HTTPException(status_code=400, detail="Esta solicitação já foi respondida.")

    solicitacao.resposta_texto = dados.resposta_texto
    solicitacao.status = "RESPONDIDO"
    solicitacao.respondido_em = datetime.now(timezone.utc)
    await db.commit()

    if solicitacao.solicitado_por_usuario_id:
        await crud_notificacoes.criar_notificacao(
            db, tenant_id, solicitacao.solicitado_por_usuario_id, tipo="SOLICITACAO_DOCUMENTO",
            titulo=f"Resposta recebida: {solicitacao.titulo}", mensagem=dados.resposta_texto[:280], link="/documentos"
        )

    return _serializar_escola(solicitacao)


async def concluir_solicitacao_escola(db: AsyncSession, tenant_id, solicitacao_id: uuid.UUID) -> dict:
    solicitacao = await _obter_solicitacao_escola(db, tenant_id, solicitacao_id)
    if solicitacao.status != "RESPONDIDO":
        raise HTTPException(status_code=400, detail="Só é possível concluir uma solicitação já respondida.")
    solicitacao.status = "CONCLUIDO"
    await db.commit()
    return _serializar_escola(solicitacao)
