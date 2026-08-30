"""
Acesso a dados e regras de negócio dos Pedidos de Transferência de
Aluno entre instituições desta plataforma — ver docstring de
models_transferencias.py para a semântica da migração.

Only aprovar_e_migrar/rejeitar (chamadas pelo Super Admin) tocam dados
fora do tenant de quem pediu — ver comentário em cruds/admin.py sobre
o porquê de ser seguro (RLS é reforço, o isolamento real vem do filtro
explícito por tenant_id, e aqui o filtro é deliberadamente cruzado).
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.core.paginacao import paginar_linhas
from app.cruds import notificacoes as crud_notificacoes
from app.schemas.transferencias import RejeitarTransferenciaRequest, SolicitacaoTransferenciaCreate
from app.database.models_transferencias import SolicitacaoTransferencia

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

    matricula = (await db.execute(
        select(Matricula).where(Matricula.aluno_id == aluno.id, Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO")
        .order_by(Matricula.ano_letivo.desc())
    )).scalars().first()
    if not matricula:
        raise HTTPException(status_code=400, detail="O aluno não tem uma matrícula ativa para transferir.")

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
    if not matricula or matricula.status_matricula != "ATIVO":
        raise HTTPException(status_code=400, detail="A matrícula de origem já não está ativa — peça um novo pedido.")

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

    matricula.status_matricula = "TRANSFERIDO"
    solicitacao.status = "CONCLUIDA"
    solicitacao.aluno_novo_id = novo_aluno.id
    solicitacao.data_decisao = datetime.now(timezone.utc)
    await db.commit()

    tenant_destino = (await db.execute(select(Tenant).where(Tenant.id == solicitacao.tenant_destino_id))).scalars().first()

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
        await crud_notificacoes.criar_notificacoes_em_lote(
            db, solicitacao.tenant_destino_id, list(gestores_destino), tipo="SOLICITACAO_TRANSFERENCIA",
            titulo="Aluno transferido — falta matricular",
            mensagem=f"{aluno.nome_completo} foi transferido para esta escola. Os dados e responsáveis já foram criados — falta atribuir turma e concluir a matrícula.",
            link="/alunos"
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
