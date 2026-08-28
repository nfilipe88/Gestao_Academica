"""
Acesso a dados do Painel Super Admin.

Ao contrário de todos os outros módulos, este é intencionalmente
multi-tenant na leitura: nenhuma função aqui filtra por tenant_id — é
o Super Admin quem gere as instituições em si. Só é alcançável através
de exigir_perfil("SUPER_ADMIN") na camada de API (app/api/v1/admin.py).
"""
import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, Usuario
from app.database.models_pessoas import Aluno, Professor
from app.database.models_diario import TipoAvaliacaoConfig
from app.database.models_billing import AssinaturaTenant, PlanoSaaS
from app.schemas.admin import (
    AssinaturaTenantInput, PlanoSaaSCreate, PlanoSaaSUpdate,
    TenantCreateAdmin, TenantStatusUpdate, ValidadeLicencaUpdate
)
from app.core.security import gerar_hash_senha
from app.core.paginacao import paginar_linhas
from app.core import revogacao
from app.cruds import notificacoes as crud_notificacoes

logger = logging.getLogger("admin")

STATUS_VALIDOS = {"ATIVO", "SUSPENSO"}

# NIF reservado ao tenant interno da plataforma (onde vivem os logins
# SUPER_ADMIN, criado por seed_super_admin.py) — nunca aparece na lista
# de escolas geridas, nem pode ser suspenso.
NIF_PLATAFORMA = "00000000000"

# A partir de quantos dias antes de expirar é que a licença começa a
# gerar alertas diários (in-app + e-mail) ao Gestor da escola e ao Super Admin.
DIAS_ALERTA_LICENCA = 7

# Sanções progressivas (dias em atraso APÓS a data de validade expirar
# — distinto de DIAS_ALERTA_LICENCA acima, que é ANTES de expirar):
#   0-14 dias de atraso: só alerta (ATIVO, acesso normal).
#   15-29 dias de atraso: BLOQUEIO_PARCIAL — a escola continua a
#     aceder normalmente (ATIVO), mas fica impedida de criar novas
#     Matrículas/Contratos Financeiros (ver esta_bloqueado_parcialmente,
#     chamada em cruds/matriculas.py e cruds/financeiro.py) — pressão
#     comercial sem cortar o serviço a meio do ano letivo.
#   30+ dias de atraso: SUSPENSA — bloqueio total (status=SUSPENSO,
#     mesmo comportamento que já existia antes desta sanção progressiva).
DIAS_BLOQUEIO_PARCIAL_LICENCA = 15
DIAS_SUSPENSAO_LICENCA = 30


def _em_periodo_teste(data_inicio: date, dias_periodo_teste: int) -> bool:
    """Calculado on-the-fly (nunca persistido) — mesma filosofia de
    esta_bloqueado_parcialmente() abaixo: "está em teste?" é sempre uma
    função da data de hoje, nunca um estado gravado que possa ficar
    dessincronizado."""
    if dias_periodo_teste <= 0:
        return False
    return (date.today() - data_inicio).days < dias_periodo_teste


async def listar_tenants(
    db: AsyncSession, page: int, page_size: int,
    nome: str | None = None, plano_id: uuid.UUID | None = None,
    usuarios_min: int | None = None, usuarios_max: int | None = None,
) -> dict:
    """Todas as instituições da plataforma (exceto o tenant interno), com
    contagens básicas de uso e o plano ativo de cada uma.

    Filtros: nome (ILIKE em nome_fantasia), plano_id (só escolas com
    assinatura ATIVA nesse plano) e usuarios_min/usuarios_max (intervalo
    de nº de utilizadores) — este último tem de entrar na query
    principal (via subquery + WHERE), não filtrar em Python depois de
    paginar, senão a paginação fica errada (páginas com menos itens do
    que page_size, ou "total" a mentir).
    """
    subq_usuarios = (
        select(Usuario.tenant_id, func.count(Usuario.id).label("total"))
        .group_by(Usuario.tenant_id).subquery()
    )
    total_usuarios_expr = func.coalesce(subq_usuarios.c.total, 0)

    query = (
        select(Tenant, total_usuarios_expr.label("total_usuarios"))
        .outerjoin(subq_usuarios, subq_usuarios.c.tenant_id == Tenant.id)
        .where(Tenant.nif != NIF_PLATAFORMA)
    )
    if nome:
        query = query.where(Tenant.nome_fantasia.ilike(f"%{nome.strip()}%"))
    if usuarios_min is not None:
        query = query.where(total_usuarios_expr >= usuarios_min)
    if usuarios_max is not None:
        query = query.where(total_usuarios_expr <= usuarios_max)
    if plano_id:
        query = query.join(
            AssinaturaTenant,
            (AssinaturaTenant.tenant_id == Tenant.id)
            & (AssinaturaTenant.status == "ATIVA")
            & (AssinaturaTenant.plano_id == plano_id)
        )
    query = query.order_by(Tenant.data_criacao.desc())

    pagina = await paginar_linhas(db, query, page, page_size)
    linhas = pagina["items"]
    if not linhas:
        pagina["items"] = []
        return pagina

    tenants = [linha[0] for linha in linhas]
    contagem_usuarios = {linha[0].id: linha[1] for linha in linhas}
    tenant_ids = [t.id for t in tenants]

    contagem_alunos = dict((await db.execute(
        select(Aluno.tenant_id, func.count(Aluno.id))
        .where(Aluno.tenant_id.in_(tenant_ids)).group_by(Aluno.tenant_id)
    )).all())
    contagem_professores = dict((await db.execute(
        select(Professor.tenant_id, func.count(Professor.id))
        .where(Professor.tenant_id.in_(tenant_ids)).group_by(Professor.tenant_id)
    )).all())

    linhas_plano = (await db.execute(
        select(AssinaturaTenant.tenant_id, PlanoSaaS.nome, PlanoSaaS.dias_periodo_teste, AssinaturaTenant.data_inicio)
        .join(PlanoSaaS, PlanoSaaS.id == AssinaturaTenant.plano_id)
        .where(AssinaturaTenant.tenant_id.in_(tenant_ids), AssinaturaTenant.status == "ATIVA")
    )).all()
    planos_por_tenant = {
        tid: {"nome_plano": nome_plano, "em_periodo_teste": _em_periodo_teste(data_inicio, dias_teste)}
        for tid, nome_plano, dias_teste, data_inicio in linhas_plano
    }

    pagina["items"] = [
        {
            "id": t.id,
            "nome_fantasia": t.nome_fantasia,
            "razao_social": t.razao_social,
            "nif": t.nif,
            "status": t.status,
            "data_validade_licenca": t.data_validade_licenca,
            "data_criacao": t.data_criacao,
            "total_usuarios": contagem_usuarios.get(t.id, 0),
            "total_alunos": contagem_alunos.get(t.id, 0),
            "total_professores": contagem_professores.get(t.id, 0),
            "nome_plano": planos_por_tenant.get(t.id, {}).get("nome_plano"),
            "em_periodo_teste": planos_por_tenant.get(t.id, {}).get("em_periodo_teste", False),
        }
        for t in tenants
    ]
    return pagina


async def criar_tenant_admin(db: AsyncSession, dados: TenantCreateAdmin) -> tuple[Tenant, Usuario]:
    """
    Onboarding gatekeeping pelo Super Admin — via de criação de escola em
    alternativa ao auto-serviço (POST /api/v1/auth/registo). A sessão
    (obter_sessao_db_admin) já corre com o role app_sistema (bypassrls),
    a mesma razão de cruds/auth.py::registar_escola: o Super Admin está a
    criar o próprio tenant, antes de existir qualquer "tenant atual".

    Espelha registar_escola quase byte a byte (mesmas validações, mesmo
    seed de TipoAvaliacaoConfig) — a única diferença é quem pode chamar
    isto (SUPER_ADMIN, via exigir_perfil na API) e por isso não precisa
    de abrir a sua própria sessão como aquela função faz.
    """
    nif_existente = (await db.execute(select(Tenant).where(Tenant.nif == dados.nif))).scalars().first()
    if nif_existente:
        raise HTTPException(status_code=400, detail="Este NIF já está registado.")

    email_existente = (await db.execute(select(Usuario).where(Usuario.email == dados.email_gestor))).scalars().first()
    if email_existente:
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    try:
        novo_tenant = Tenant(nome_fantasia=dados.nome_fantasia, nif=dados.nif, status="ATIVO")
        db.add(novo_tenant)
        await db.flush()

        novo_gestor = Usuario(
            tenant_id=novo_tenant.id,
            nome_completo=dados.nome_gestor,
            email=dados.email_gestor,
            senha_hash=gerar_hash_senha(dados.palavra_passe),
            perfil_acesso="GESTOR",
        )
        db.add(novo_gestor)

        db.add(TipoAvaliacaoConfig(tenant_id=novo_tenant.id, nome="CONTINUA", requer_agendamento=False, ativo=True))
        db.add(TipoAvaliacaoConfig(tenant_id=novo_tenant.id, nome="PROVA", requer_agendamento=True, ativo=True))

        await db.commit()
        await db.refresh(novo_tenant)
        await db.refresh(novo_gestor)
        return novo_tenant, novo_gestor
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar a escola: {str(e)}")


async def atualizar_status_tenant(db: AsyncSession, tenant_id: uuid.UUID, dados: TenantStatusUpdate) -> Tenant:
    """Suspende ou reativa uma instituição — RN02: bloqueia o login de todos os seus utilizadores (ver cruds/auth.py::autenticar)."""
    if dados.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use um de: {', '.join(sorted(STATUS_VALIDOS))}.")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    if tenant.nif == NIF_PLATAFORMA:
        raise HTTPException(status_code=400, detail="Não é possível alterar o estado do tenant interno da plataforma.")

    tenant.status = dados.status
    await db.commit()
    await db.refresh(tenant)
    if tenant.status != "ATIVO":
        # Sem isto, todos os utilizadores desta escola continuavam com
        # acesso normal até os tokens já emitidos expirarem sozinhos
        # (até ACCESS_TOKEN_EXPIRE_MINUTES) — a suspensão só bloqueava
        # LOGINS novos, não sessões já abertas (ver cruds/auth.py::autenticar).
        await revogacao.revogar_tenant(tenant.id)
    return tenant


async def atualizar_validade_licenca(db: AsyncSession, tenant_id: uuid.UUID, dados: ValidadeLicencaUpdate) -> Tenant:
    """Define (ou remove, se None) a data de validade da licença — ver job_validade_licenca_diaria no scheduler."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    if tenant.nif == NIF_PLATAFORMA:
        raise HTTPException(status_code=400, detail="Não é possível definir validade de licença para o tenant interno da plataforma.")

    tenant.data_validade_licenca = dados.data_validade_licenca
    await db.commit()
    await db.refresh(tenant)
    return tenant


# ==========================================
# JOB DIÁRIO (chamado por app/core/scheduler.py)
# ==========================================
async def _destinatarios_alerta_licenca(db: AsyncSession, tenant_id) -> list[uuid.UUID]:
    """GESTOR(es) da escola + todos os logins SUPER_ADMIN."""
    gestores = (await db.execute(
        select(Usuario.id).where(Usuario.tenant_id == tenant_id, Usuario.perfil_acesso == "GESTOR")
    )).scalars().all()

    tenant_plataforma = (await db.execute(select(Tenant.id).where(Tenant.nif == NIF_PLATAFORMA))).scalar_one_or_none()
    super_admins = []
    if tenant_plataforma:
        super_admins = (await db.execute(
            select(Usuario.id).where(Usuario.tenant_id == tenant_plataforma, Usuario.perfil_acesso == "SUPER_ADMIN")
        )).scalars().all()

    return list(gestores) + list(super_admins)


async def processar_validade_licencas(db: AsyncSession, agendar_email) -> dict:
    """
    Percorre todas as escolas com data de validade de licença definida
    e aplica a sanção progressiva correspondente aos dias em atraso
    (ver constantes DIAS_BLOQUEIO_PARCIAL_LICENCA/DIAS_SUSPENSAO_LICENCA
    acima) — ou o alerta pré-expiração de sempre, se ainda não expirou.
    BLOQUEIO_PARCIAL nunca muda tenant.status (a escola continua ATIVO,
    só perde a capacidade de criar Matrículas/Contratos — ver
    esta_bloqueado_parcialmente); só a suspensão aos 30 dias muda o
    status. Devolve um resumo para o log/teste manual.
    """
    hoje = date.today()
    limite_alerta = hoje + timedelta(days=DIAS_ALERTA_LICENCA)

    tenants = (await db.execute(
        select(Tenant).where(
            Tenant.nif != NIF_PLATAFORMA,
            Tenant.data_validade_licenca.isnot(None),
            Tenant.status == "ATIVO",
        )
    )).scalars().all()

    resumo = {"suspensos": 0, "bloqueados_parcial": 0, "alertados": 0}

    for tenant in tenants:
        destinatarios = await _destinatarios_alerta_licenca(db, tenant.id)
        emails = (await db.execute(
            select(Usuario.email).where(Usuario.id.in_(destinatarios))
        )).scalars().all() if destinatarios else []

        dias_atraso = (hoje - tenant.data_validade_licenca).days  # negativo = ainda não expirou

        if dias_atraso >= DIAS_SUSPENSAO_LICENCA:
            tenant.status = "SUSPENSO"
            titulo = "Licença expirada há 30+ dias — acesso suspenso"
            mensagem = f"A licença de {tenant.nome_fantasia} está por regularizar há {dias_atraso} dias e o acesso foi automaticamente suspenso."
            resumo["suspensos"] += 1
        elif dias_atraso >= DIAS_BLOQUEIO_PARCIAL_LICENCA:
            titulo = "Licença vencida há 15+ dias — novas matrículas bloqueadas"
            mensagem = (
                f"A licença de {tenant.nome_fantasia} está por regularizar há {dias_atraso} dias. "
                f"O acesso continua normal, mas não é possível criar novas Matrículas ou Contratos Financeiros até regularizar — "
                f"a partir de {DIAS_SUSPENSAO_LICENCA} dias em atraso o acesso é suspenso na totalidade."
            )
            resumo["bloqueados_parcial"] += 1
        elif dias_atraso >= 0:
            titulo = "Licença vencida"
            mensagem = f"A licença de {tenant.nome_fantasia} venceu há {dias_atraso} dia(s). Regularize a situação para evitar restrições de acesso."
            resumo["alertados"] += 1
        elif tenant.data_validade_licenca <= limite_alerta:
            dias_restantes = -dias_atraso
            titulo = "Licença a expirar em breve"
            mensagem = f"A licença de {tenant.nome_fantasia} expira em {tenant.data_validade_licenca.strftime('%d/%m/%Y')} ({dias_restantes} dia(s))."
            resumo["alertados"] += 1
        else:
            continue

        try:
            await crud_notificacoes.criar_notificacoes_em_lote(
                db, tenant.id, destinatarios, tipo="LICENCA", titulo=titulo, mensagem=mensagem, link="/admin"
            )
            await db.commit()
            if dias_atraso >= DIAS_SUSPENSAO_LICENCA:
                # Mesma razão da suspensão manual (ver atualizar_status_tenant)
                # — sem isto, sessões já abertas continuavam a funcionar
                # normalmente até expirarem sozinhas.
                await revogacao.revogar_tenant(tenant.id)
        except Exception:
            logger.exception("Falha ao notificar/atualizar a licença da escola %s (%s).", tenant.nome_fantasia, tenant.id)
            await db.rollback()
            continue

        from app.core.email import enviar_email, template_base
        for email in emails:
            if email:
                await agendar_email(enviar_email, destinatario=email, assunto=titulo, corpo_html=template_base(titulo, f"<p>{mensagem}</p>"))

    return resumo


async def esta_bloqueado_parcialmente(db: AsyncSession, tenant_id) -> bool:
    """
    Chamado por cruds/matriculas.py::criar_matricula e
    cruds/financeiro.py::criar_contrato antes de criar o registo — ver
    DIAS_BLOQUEIO_PARCIAL_LICENCA acima. Calculado on-the-fly a partir
    de Tenant.data_validade_licenca (nunca persistido à parte, mesmo
    princípio do cálculo de juros/multa em cruds/financeiro.py::calcular_situacao_fatura)
    para nunca poder ficar dessincronizado da data real.
    """
    validade = (await db.execute(
        select(Tenant.data_validade_licenca).where(Tenant.id == tenant_id)
    )).scalar_one_or_none()
    if not validade:
        return False
    return (date.today() - validade).days >= DIAS_BLOQUEIO_PARCIAL_LICENCA


# ==========================================
# SAAS BILLING — Planos e Assinaturas
# ==========================================
async def listar_planos(db: AsyncSession) -> list[PlanoSaaS]:
    return (await db.execute(select(PlanoSaaS).order_by(PlanoSaaS.preco_mensal))).scalars().all()


async def criar_plano(db: AsyncSession, dados: PlanoSaaSCreate) -> PlanoSaaS:
    ja_existe = (await db.execute(select(PlanoSaaS).where(PlanoSaaS.nome == dados.nome))).scalars().first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Já existe um plano com este nome.")

    novo = PlanoSaaS(
        nome=dados.nome.strip(), preco_mensal=dados.preco_mensal,
        limite_alunos=dados.limite_alunos, descricao=dados.descricao,
        dias_periodo_teste=dados.dias_periodo_teste,
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return novo


async def _obter_plano(db: AsyncSession, plano_id: uuid.UUID) -> PlanoSaaS:
    plano = (await db.execute(select(PlanoSaaS).where(PlanoSaaS.id == plano_id))).scalars().first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    return plano


async def atualizar_plano(db: AsyncSession, plano_id: uuid.UUID, dados: PlanoSaaSUpdate) -> PlanoSaaS:
    plano = await _obter_plano(db, plano_id)
    duplicado = (await db.execute(
        select(PlanoSaaS).where(PlanoSaaS.nome == dados.nome, PlanoSaaS.id != plano_id)
    )).scalars().first()
    if duplicado:
        raise HTTPException(status_code=400, detail="Já existe um plano com este nome.")

    plano.nome = dados.nome.strip()
    plano.preco_mensal = dados.preco_mensal
    plano.limite_alunos = dados.limite_alunos
    plano.descricao = dados.descricao
    plano.dias_periodo_teste = dados.dias_periodo_teste
    plano.ativo = dados.ativo
    await db.commit()
    await db.refresh(plano)
    return plano


async def apagar_plano(db: AsyncSession, plano_id: uuid.UUID) -> None:
    plano = await _obter_plano(db, plano_id)
    em_uso = (await db.execute(select(AssinaturaTenant).where(AssinaturaTenant.plano_id == plano_id))).scalars().first()
    if em_uso:
        raise HTTPException(status_code=400, detail="Este plano tem escolas assinadas — desative-o em vez de apagar.")
    await db.delete(plano)
    await db.commit()


async def obter_assinatura_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> dict | None:
    linha = (await db.execute(
        select(AssinaturaTenant, PlanoSaaS.nome, PlanoSaaS.preco_mensal, PlanoSaaS.dias_periodo_teste)
        .join(PlanoSaaS, PlanoSaaS.id == AssinaturaTenant.plano_id)
        .where(AssinaturaTenant.tenant_id == tenant_id)
    )).first()
    if not linha:
        return None
    assinatura, nome_plano, preco_mensal, dias_periodo_teste = linha
    return {
        "id": assinatura.id, "plano_id": assinatura.plano_id, "nome_plano": nome_plano, "preco_mensal": preco_mensal,
        "data_inicio": assinatura.data_inicio, "proxima_cobranca": assinatura.proxima_cobranca, "status": assinatura.status,
        "em_periodo_teste": _em_periodo_teste(assinatura.data_inicio, dias_periodo_teste),
    }


async def definir_assinatura_tenant(db: AsyncSession, tenant_id: uuid.UUID, dados: AssinaturaTenantInput) -> dict:
    """Upsert: associa (ou troca) o plano da escola — não guarda histórico de planos anteriores nesta primeira versão."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Instituição não encontrada.")
    await _obter_plano(db, dados.plano_id)  # 404 se o plano não existir

    existente = (await db.execute(select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant_id))).scalars().first()
    if existente:
        existente.plano_id = dados.plano_id
        existente.proxima_cobranca = dados.proxima_cobranca
        existente.status = "ATIVA"
    else:
        db.add(AssinaturaTenant(
            tenant_id=tenant_id, plano_id=dados.plano_id,
            data_inicio=date.today(), proxima_cobranca=dados.proxima_cobranca, status="ATIVA"
        ))
    await db.commit()
    return await obter_assinatura_tenant(db, tenant_id)


async def cancelar_assinatura_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    assinatura = (await db.execute(select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant_id))).scalars().first()
    if not assinatura:
        raise HTTPException(status_code=404, detail="Esta escola não tem assinatura.")
    assinatura.status = "CANCELADA"
    await db.commit()


async def obter_resumo_mrr(db: AsyncSession) -> dict:
    """MRR (receita mensal recorrente) = soma dos preços dos planos das assinaturas ATIVA — cálculo simples, sem pro-rata."""
    linhas = (await db.execute(
        select(PlanoSaaS.nome, PlanoSaaS.preco_mensal, func.count(AssinaturaTenant.id))
        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoSaaS.id)
        .where(AssinaturaTenant.status == "ATIVA")
        .group_by(PlanoSaaS.nome, PlanoSaaS.preco_mensal)
    )).all()

    por_plano = [
        {"nome_plano": nome, "preco_mensal": preco, "total_assinaturas": total, "receita_mensal": preco * total}
        for nome, preco, total in linhas
    ]
    return {
        "mrr": sum((p["receita_mensal"] for p in por_plano), Decimal("0.00")),
        "total_assinaturas_ativas": sum(p["total_assinaturas"] for p in por_plano),
        "por_plano": por_plano,
    }
