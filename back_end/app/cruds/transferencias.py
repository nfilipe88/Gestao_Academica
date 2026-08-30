"""
Acesso a dados e regras de negócio dos Pedidos de Transferência de
Aluno entre instituições desta plataforma — ver docstring de
models_transferencias.py para a semântica da migração.

Only aprovar_e_migrar/rejeitar (chamadas pelo Super Admin) tocam dados
fora do tenant de quem pediu — ver comentário em cruds/admin.py sobre
o porquê de ser seguro (RLS é reforço, o isolamento real vem do filtro
explícito por tenant_id, e aqui o filtro é deliberadamente cruzado).
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.core import documentos_pdf, storage
from app.core.paginacao import paginar_linhas
from app.cruds import alunos as crud_alunos
from app.cruds import documentos as crud_documentos
from app.cruds import notificacoes as crud_notificacoes
from app.schemas.transferencias import RejeitarTransferenciaRequest, SolicitacaoTransferenciaCreate
from app.database.models_transferencias import SolicitacaoTransferencia

logger = logging.getLogger("transferencias")

NIF_PLATAFORMA = "00000000000"


def _serializar(
    solicitacao: SolicitacaoTransferencia, aluno_nome: str | None = None,
    nome_origem: str | None = None, nome_destino: str | None = None
) -> dict:
    return {
        "id": solicitacao.id,
        "tenant_id": solicitacao.tenant_id,
        "nome_instituicao_origem": nome_origem,
        "aluno_id": solicitacao.aluno_id,
        "aluno_nome": aluno_nome,
        "tenant_destino_id": solicitacao.tenant_destino_id,
        "nome_instituicao_destino": nome_destino,
        "nif_destino": solicitacao.nif_destino,
        "motivo": solicitacao.motivo,
        "status": solicitacao.status,
        "observacoes_decisao": solicitacao.observacoes_decisao,
        "aluno_novo_id": solicitacao.aluno_novo_id,
        "data_solicitacao": solicitacao.data_solicitacao,
        "data_decisao": solicitacao.data_decisao,
    }


async def criar_solicitacao(db: AsyncSession, tenant_id, utilizador: dict, dados: SolicitacaoTransferenciaCreate) -> dict:
    aluno = (await db.execute(select(Aluno).where(Aluno.id == dados.aluno_id, Aluno.tenant_id == tenant_id))).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    # A matrícula mais recente do aluno, seja qual for o estado — depois
    # verifica-se se esse estado é um dos dois que legitimam um pedido
    # (ver docstring de models_transferencias.py): ATIVO (transferência
    # a quente) ou CICLO_CONCLUIDO (Reingresso cross-escola, o aluno já
    # tinha saído desta escola e só agora aparece a continuar noutra).
    matricula = (await db.execute(
        select(Matricula).where(Matricula.aluno_id == aluno.id, Matricula.tenant_id == tenant_id)
        .order_by(Matricula.ano_letivo.desc())
    )).scalars().first()
    if not matricula or matricula.status_matricula not in ("ATIVO", "CICLO_CONCLUIDO"):
        raise HTTPException(
            status_code=400,
            detail="Só é possível pedir transferência/reingresso para um aluno com matrícula ativa, "
                   "ou com Fim de Ciclo (Reingresso cross-escola) — este aluno não está em nenhum dos dois casos."
        )

    ja_pendente = (await db.execute(
        select(SolicitacaoTransferencia).where(SolicitacaoTransferencia.aluno_id == aluno.id, SolicitacaoTransferencia.status == "PENDENTE")
    )).scalars().first()
    if ja_pendente:
        raise HTTPException(status_code=400, detail="Já existe um pedido de transferência pendente para este aluno.")

    nif_limpo = dados.nif_destino.strip()
    if nif_limpo == NIF_PLATAFORMA:
        raise HTTPException(status_code=400, detail="NIF de destino inválido.")
    tenant_destino = (await db.execute(select(Tenant).where(Tenant.nif == nif_limpo))).scalars().first()
    if not tenant_destino:
        raise HTTPException(status_code=404, detail="Não foi encontrada nenhuma instituição desta plataforma com esse NIF.")
    if tenant_destino.id == tenant_id:
        raise HTTPException(status_code=400, detail="A instituição de destino não pode ser a mesma que a de origem.")
    if tenant_destino.status != "ATIVO":
        raise HTTPException(status_code=400, detail="A instituição de destino não está ativa na plataforma.")

    nova = SolicitacaoTransferencia(
        tenant_id=tenant_id,
        aluno_id=aluno.id,
        matricula_id=matricula.id,
        solicitado_por_usuario_id=utilizador["usuario_id"],
        tenant_destino_id=tenant_destino.id,
        nif_destino=nif_limpo,
        motivo=dados.motivo,
        status="PENDENTE",
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)

    # Notifica todos os logins SUPER_ADMIN — só eles têm alcance sobre
    # duas instituições ao mesmo tempo para poder decidir isto.
    tenant_plataforma = (await db.execute(select(Tenant.id).where(Tenant.nif == NIF_PLATAFORMA))).scalar_one_or_none()
    if tenant_plataforma:
        tenant_origem = (await db.execute(select(Tenant.nome_fantasia).where(Tenant.id == tenant_id))).scalar_one_or_none()
        super_admins = (await db.execute(
            select(Usuario.id).where(Usuario.tenant_id == tenant_plataforma, Usuario.perfil_acesso == "SUPER_ADMIN")
        )).scalars().all()
        await crud_notificacoes.criar_notificacoes_em_lote(
            db, tenant_plataforma, list(super_admins), tipo="SOLICITACAO_TRANSFERENCIA",
            titulo="Novo pedido de transferência de aluno",
            mensagem=f"{aluno.nome_completo} — de {tenant_origem or 'instituição de origem'} para {tenant_destino.nome_fantasia}.",
            link="/admin/transferencias"
        )

    return _serializar(nova, aluno_nome=aluno.nome_completo, nome_destino=tenant_destino.nome_fantasia)


async def listar_minhas_solicitacoes(
    db: AsyncSession, tenant_id, page: int, page_size: int,
    status: str | None = None, data_inicio=None, data_fim=None
) -> dict:
    query = (
        select(SolicitacaoTransferencia, Aluno.nome_completo, Tenant.nome_fantasia)
        .join(Aluno, Aluno.id == SolicitacaoTransferencia.aluno_id)
        .join(Tenant, Tenant.id == SolicitacaoTransferencia.tenant_destino_id)
        .where(SolicitacaoTransferencia.tenant_id == tenant_id)
    )
    if status:
        query = query.where(SolicitacaoTransferencia.status == status)
    if data_inicio:
        query = query.where(SolicitacaoTransferencia.data_solicitacao >= data_inicio)
    if data_fim:
        query = query.where(SolicitacaoTransferencia.data_solicitacao < data_fim + timedelta(days=1))
    query = query.order_by(SolicitacaoTransferencia.data_solicitacao.desc())
    pagina = await paginar_linhas(db, query, page, page_size)
    pagina["items"] = [_serializar(s, aluno_nome=nome_aluno, nome_destino=nome_destino) for s, nome_aluno, nome_destino in pagina["items"]]
    return pagina


async def listar_solicitacoes_super_admin(db: AsyncSession, page: int, page_size: int) -> dict:
    """Cross-tenant deliberado — ver docstring do módulo."""
    OrigemTenant = Tenant
    from sqlalchemy.orm import aliased
    DestinoTenant = aliased(Tenant)

    query = (
        select(SolicitacaoTransferencia, Aluno.nome_completo, OrigemTenant.nome_fantasia, DestinoTenant.nome_fantasia)
        .join(Aluno, Aluno.id == SolicitacaoTransferencia.aluno_id)
        .join(OrigemTenant, OrigemTenant.id == SolicitacaoTransferencia.tenant_id)
        .join(DestinoTenant, DestinoTenant.id == SolicitacaoTransferencia.tenant_destino_id)
        .order_by(SolicitacaoTransferencia.data_solicitacao.desc())
    )
    pagina = await paginar_linhas(db, query, page, page_size)
    pagina["items"] = [
        _serializar(s, aluno_nome=nome_aluno, nome_origem=nome_origem, nome_destino=nome_destino)
        for s, nome_aluno, nome_origem, nome_destino in pagina["items"]
    ]
    return pagina


async def _obter_solicitacao(db: AsyncSession, solicitacao_id: uuid.UUID) -> SolicitacaoTransferencia:
    solicitacao = (await db.execute(
        select(SolicitacaoTransferencia).where(SolicitacaoTransferencia.id == solicitacao_id)
    )).scalars().first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Pedido de transferência não encontrado.")
    return solicitacao


async def aprovar_e_migrar(db: AsyncSession, solicitacao_id: uuid.UUID) -> dict:
    solicitacao = await _obter_solicitacao(db, solicitacao_id)
    if solicitacao.status != "PENDENTE":
        raise HTTPException(status_code=400, detail="Este pedido já foi decidido.")

    aluno = (await db.execute(select(Aluno).where(Aluno.id == solicitacao.aluno_id))).scalars().first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno de origem não encontrado.")
    matricula = (await db.execute(select(Matricula).where(Matricula.id == solicitacao.matricula_id))).scalars().first()
    if not matricula or matricula.status_matricula not in ("ATIVO", "CICLO_CONCLUIDO"):
        raise HTTPException(
            status_code=400,
            detail="A matrícula de origem já não está num estado válido para aprovar este pedido — peça um novo pedido."
        )
    # Só uma transferência "a quente" (matrícula ainda ATIVO) fecha a
    # matrícula de origem como TRANSFERIDO. Reingresso cross-escola
    # (origem já CICLO_CONCLUIDO — ver docstring de
    # models_transferencias.py) não mexe nela: o Fim de Ciclo já
    # aconteceu e continua a ser verdade, só o aluno reapareceu depois.
    origem_era_ciclo_concluido = matricula.status_matricula == "CICLO_CONCLUIDO"

    vinculos = (await db.execute(
        select(AlunoResponsavel, ResponsavelFinanceiroLegal)
        .join(ResponsavelFinanceiroLegal, ResponsavelFinanceiroLegal.id == AlunoResponsavel.responsavel_id)
        .where(AlunoResponsavel.aluno_id == aluno.id)
    )).all()

    novo_aluno = Aluno(
        tenant_id=solicitacao.tenant_destino_id,
        matricula_interna=aluno.matricula_interna,
        nome_completo=aluno.nome_completo,
        data_nascimento=aluno.data_nascimento,
        numero_documento=aluno.numero_documento,
    )
    db.add(novo_aluno)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Já existe um aluno com esta matrícula interna na instituição de destino. Contacte o suporte para resolver manualmente."
        )

    for vinculo, responsavel in vinculos:
        novo_responsavel = ResponsavelFinanceiroLegal(
            tenant_id=solicitacao.tenant_destino_id,
            nome_completo=responsavel.nome_completo,
            numero_documento=responsavel.numero_documento,
            telefone_contato=responsavel.telefone_contato,
            email=responsavel.email,
        )
        db.add(novo_responsavel)
        await db.flush()
        db.add(AlunoResponsavel(
            tenant_id=solicitacao.tenant_destino_id,
            aluno_id=novo_aluno.id,
            responsavel_id=novo_responsavel.id,
            tipo_parentesco=vinculo.tipo_parentesco,
            responsavel_financeiro=vinculo.responsavel_financeiro,
        ))

    if not origem_era_ciclo_concluido:
        matricula.status_matricula = "TRANSFERIDO"
    solicitacao.status = "CONCLUIDA"
    solicitacao.aluno_novo_id = novo_aluno.id
    solicitacao.data_decisao = datetime.now(timezone.utc)
    await db.commit()

    tenant_destino = (await db.execute(select(Tenant).where(Tenant.id == solicitacao.tenant_destino_id))).scalars().first()

    # Histórico Escolar automático: a migração em si nunca copia
    # notas/frequência para as tabelas académicas da escola de destino
    # (currículos e escalas de nota diferem de escola para escola — ver
    # docstring de models_transferencias.py), mas a escola de destino
    # não devia ficar com um aluno sem NENHUM rasto do percurso anterior
    # à espera que a família peça e pague um Histórico Escolar à parte
    # (ver Solicitações de Documentos). Em vez disso, gera-se aqui o
    # mesmo PDF que esse pedido geraria — a partir dos dados da escola
    # de ORIGEM — e anexa-se como documento opaco ao aluno recém-criado
    # na escola de destino (AlunoDocumento, ver cruds/alunos.py).
    # Best-effort de propósito: uma falha aqui (ex.: storage em baixo)
    # nunca deve desfazer a migração de identidade já confirmada acima.
    try:
        tenant_origem = (await db.execute(select(Tenant).where(Tenant.id == solicitacao.tenant_id))).scalars().first()
        escola_origem = {
            "nome": tenant_origem.nome_fantasia if tenant_origem else "",
            "razao_social": tenant_origem.razao_social if tenant_origem else "",
            "nif": tenant_origem.nif if tenant_origem else "",
            "morada": tenant_origem.morada if tenant_origem else None,
            "contacto": " · ".join(filter(None, [tenant_origem.telefone_contacto, tenant_origem.email_contacto])) if tenant_origem else None,
            "logo_data_uri": await storage.obter_logo_data_uri(tenant_origem),
        }
        contexto = await crud_documentos.construir_contexto_historico_escolar(db, solicitacao.tenant_id, aluno)
        template_personalizado = await crud_documentos.obter_template_personalizado_ativo(db, solicitacao.tenant_id, "HISTORICO_ESCOLAR")
        pdf_bytes = documentos_pdf.gerar_pdf_documento(
            "HISTORICO_ESCOLAR", escola_origem, contexto,
            corpo_html_personalizado=template_personalizado.corpo_html if template_personalizado else None
        )
        await crud_alunos.anexar_documento_gerado(
            db, solicitacao.tenant_destino_id, novo_aluno.id,
            descricao=f"Histórico Escolar — {escola_origem['nome'] or 'instituição de origem'}",
            nome_ficheiro="historico-escolar.pdf", conteudo_pdf=pdf_bytes,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Falha a gerar/anexar o Histórico Escolar automático na migração %s", solicitacao.id)

    if solicitacao.solicitado_por_usuario_id:
        await crud_notificacoes.criar_notificacao(
            db, solicitacao.tenant_id, solicitacao.solicitado_por_usuario_id, tipo="SOLICITACAO_TRANSFERENCIA",
            titulo="Transferência concluída",
            mensagem=f"A transferência de {aluno.nome_completo} para {tenant_destino.nome_fantasia if tenant_destino else 'a instituição de destino'} foi aprovada e concluída.",
            link="/alunos"
        )

    # A escola de destino ganhou um aluno (já com identidade e
    # responsáveis criados) mas SEM matrícula — precisa de o colocar
    # numa turma. Sem isto, só ficava sabendo por acaso, ao abrir a
    # lista de Alunos; quem pediu (escola de origem) já é notificado
    # acima, mas quem tem de agir a seguir é a escola de destino.
    gestores_destino = (await db.execute(
        select(Usuario.id).where(
            Usuario.tenant_id == solicitacao.tenant_destino_id, Usuario.perfil_acesso.in_(["GESTOR", "SECRETARIA"])
        )
    )).scalars().all()
    if gestores_destino:
        if origem_era_ciclo_concluido:
            titulo_destino = "Aluno reingressou — falta matricular"
            mensagem_destino = (
                f"{aluno.nome_completo} reingressou nesta escola (já tinha concluído o ciclo na instituição de "
                f"origem). Os dados e responsáveis já foram criados — falta atribuir turma e concluir a matrícula."
            )
        else:
            titulo_destino = "Aluno transferido — falta matricular"
            mensagem_destino = (
                f"{aluno.nome_completo} foi transferido para esta escola. Os dados e responsáveis já foram "
                f"criados — falta atribuir turma e concluir a matrícula."
            )
        await crud_notificacoes.criar_notificacoes_em_lote(
            db, solicitacao.tenant_destino_id, list(gestores_destino), tipo="SOLICITACAO_TRANSFERENCIA",
            titulo=titulo_destino, mensagem=mensagem_destino, link="/alunos"
        )

    return _serializar(solicitacao, aluno_nome=aluno.nome_completo)


async def rejeitar(db: AsyncSession, solicitacao_id: uuid.UUID, dados: RejeitarTransferenciaRequest) -> dict:
    solicitacao = await _obter_solicitacao(db, solicitacao_id)
    if solicitacao.status != "PENDENTE":
        raise HTTPException(status_code=400, detail="Este pedido já foi decidido.")

    solicitacao.status = "REJEITADA"
    solicitacao.observacoes_decisao = dados.observacoes
    solicitacao.data_decisao = datetime.now(timezone.utc)
    await db.commit()

    if solicitacao.solicitado_por_usuario_id:
        aluno = (await db.execute(select(Aluno).where(Aluno.id == solicitacao.aluno_id))).scalars().first()
        await crud_notificacoes.criar_notificacao(
            db, solicitacao.tenant_id, solicitacao.solicitado_por_usuario_id, tipo="SOLICITACAO_TRANSFERENCIA",
            titulo="Pedido de transferência rejeitado",
            mensagem=f"O pedido de transferência de {aluno.nome_completo if aluno else 'aluno'} foi rejeitado: {dados.observacoes}",
            link="/alunos"
        )

    return _serializar(solicitacao)
