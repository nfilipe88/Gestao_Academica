import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db_admin, obter_sessao_db_cross_tenant
from app.core.security import exigir_perfil
from app.core import estatisticas_excel
from app.schemas.admin import (
    AssinaturaTenantInput, PlanoSaaSCreate, PlanoSaaSOut, PlanoSaaSUpdate,
    IsencaoLimiteAlunosUpdate, MembroEquipaCreate, MembroEquipaOut, TenantCreateAdmin, TenantStatusUpdate, ValidadeLicencaUpdate
)
from app.schemas.usuarios import AtivoUpdate, PerfilAcessoUpdate, SecretariaCreate
from app.schemas.financeiro import DespesaCreate
from app.core.email import enviar_email, escapar, template_base
from app.core import eventos_seguranca, fila_notificacoes
from app.cruds import admin as crud_admin
from app.cruds import usuarios as crud_usuarios
from app.cruds import auditoria as crud_auditoria
from app.cruds import suporte as crud_suporte
from app.cruds import estatisticas as crud_estatisticas
from app.cruds import financeiro as crud_financeiro
from app.cruds import seguranca as crud_seguranca
from app.schemas.comum import PaginaOut
from app.schemas.seguranca import BloqueioIpOut, EventoSegurancaOut
from app.schemas.suporte import MensagemTicketCreate, TicketAdminComMensagens, TicketEstadoUpdate

router = APIRouter(prefix="/api/v1/admin", tags=["Painel Super Admin"])

# Único perfil que existe fora do contexto de uma escola cliente — gere
# as instituições em si, não os dados académicos de nenhuma delas.
_PODE_ACEDER = exigir_perfil("SUPER_ADMIN")

# Equipa da plataforma = Super Admin + Suporte. O Suporte ajuda as escolas
# (tickets, consulta das escolas e do seu pessoal, desbloquear pessoas,
# eventos de segurança), mas não suspende escolas, não mexe em planos/
# faturação/permissões nem cria contas — isso fica só com o Super Admin.
# Só as rotas abaixo que usam _EQUIPA/_sessao_equipa estão abertas ao Suporte.
_EQUIPA = exigir_perfil("SUPER_ADMIN", "SUPORTE")
_sessao_equipa = obter_sessao_db_cross_tenant("SUPER_ADMIN", "SUPORTE")


@router.get("/tenants")
async def listar_tenants(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    nome: str | None = Query(None), plano_id: uuid.UUID | None = Query(None),
    usuarios_min: int | None = Query(None, ge=0), usuarios_max: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(_sessao_equipa),
    utilizador: dict = Depends(_EQUIPA)
):
    """Lista todas as instituições (tenants) da plataforma, com contagens básicas de uso e o plano ativo de cada uma."""
    return await crud_admin.listar_tenants(db, page, page_size, nome, plano_id, usuarios_min, usuarios_max)


@router.post("/tenants", status_code=201)
async def criar_tenant(
    dados: TenantCreateAdmin,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Cria uma escola (Tenant) + primeiro Gestor diretamente — onboarding gatekeeping pelo Super Admin, em alternativa ao auto-serviço em /auth/registo."""
    novo_tenant, novo_gestor = await crud_admin.criar_tenant_admin(db, dados)

    await fila_notificacoes.agendar_email(
        enviar_email,
        destinatario=dados.email_gestor,
        assunto=f"Bem-vindo(a), {dados.nome_fantasia} já está na plataforma!",
        corpo_html=template_base(
            "Escola criada com sucesso!",
            f"""
            <p>Olá {escapar(dados.nome_gestor)},</p>
            <p>A instituição <strong>{escapar(dados.nome_fantasia)}</strong> foi criada na plataforma de Gestão Académica.</p>
            <p>Já pode iniciar sessão com o e-mail <strong>{escapar(dados.email_gestor)}</strong> para começar a configurar cursos, turmas e alunos.</p>
            """
        )
    )

    return {"mensagem": f'Escola "{novo_tenant.nome_fantasia}" criada com sucesso.', "id": novo_tenant.id}


@router.patch("/tenants/{tenant_id}/status")
async def atualizar_status_tenant(
    tenant_id: uuid.UUID,
    dados: TenantStatusUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Desativa (SUSPENSO) ou ativa (ATIVO) uma instituição — bloqueia/desbloqueia o login de todos os seus
    utilizadores. Nunca elimina dados (retenção legal de 15 anos)."""
    tenant = await crud_admin.atualizar_status_tenant(db, tenant_id, dados)
    return {"mensagem": f"{tenant.nome_fantasia} agora está {'ativa' if tenant.status == 'ATIVO' else 'desativada'}.", "status": tenant.status}


@router.patch("/tenants/{tenant_id}/isencao-limite-alunos")
async def atualizar_isencao_limite_alunos(
    tenant_id: uuid.UUID,
    dados: IsencaoLimiteAlunosUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Concede ou retira a isenção do limite de alunos do plano a uma instituição."""
    tenant = await crud_admin.atualizar_isencao_limite_alunos(db, tenant_id, dados)
    return {
        "mensagem": f"{tenant.nome_fantasia} {'está agora isenta' if tenant.isento_limite_alunos else 'deixou de estar isenta'} do limite de alunos.",
        "isento_limite_alunos": tenant.isento_limite_alunos,
    }


@router.patch("/tenants/{tenant_id}/validade-licenca")
async def atualizar_validade_licenca(
    tenant_id: uuid.UUID,
    dados: ValidadeLicencaUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Define a data de validade da licença — o scheduler alerta e suspende automaticamente ao expirar."""
    tenant = await crud_admin.atualizar_validade_licenca(db, tenant_id, dados)
    return {
        "mensagem": f"Validade da licença de {tenant.nome_fantasia} atualizada.",
        "data_validade_licenca": tenant.data_validade_licenca
    }


@router.post("/validade-licenca/processar")
async def processar_validade_licencas(
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """
    Disparo manual do alerta/suspensão automática por validade de
    licença — útil para testar já; o job diário em
    app/core/scheduler.py já corre isto sozinho, todos os dias às 07:00.
    """
    resumo = await crud_admin.processar_validade_licencas(db, fila_notificacoes.agendar_email)
    return {"mensagem": "Validade de licenças processada.", **resumo}


# ==========================================
# SAAS BILLING — Planos, Assinaturas e MRR
# ==========================================
@router.get("/planos", response_model=list[PlanoSaaSOut])
async def listar_planos(
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Catálogo de planos comerciais (ex.: Bronze/Prata/Ouro)."""
    return await crud_admin.listar_planos(db)


@router.post("/planos", status_code=201, response_model=PlanoSaaSOut)
async def criar_plano(
    dados: PlanoSaaSCreate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_admin.criar_plano(db, dados)


@router.patch("/planos/{plano_id}", response_model=PlanoSaaSOut)
async def atualizar_plano(
    plano_id: uuid.UUID,
    dados: PlanoSaaSUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_admin.atualizar_plano(db, plano_id, dados)


@router.delete("/planos/{plano_id}", status_code=204)
async def apagar_plano(
    plano_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    await crud_admin.apagar_plano(db, plano_id)


@router.get("/mrr")
async def obter_resumo_mrr(
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Receita mensal recorrente — soma dos preços dos planos das assinaturas ativas, por plano e total."""
    return await crud_admin.obter_resumo_mrr(db)


@router.get("/tenants/{tenant_id}/assinatura")
async def obter_assinatura_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    assinatura = await crud_admin.obter_assinatura_tenant(db, tenant_id)
    return assinatura or {}


@router.put("/tenants/{tenant_id}/assinatura")
async def definir_assinatura_tenant(
    tenant_id: uuid.UUID,
    dados: AssinaturaTenantInput,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Associa (ou troca) o plano comercial desta escola."""
    return await crud_admin.definir_assinatura_tenant(db, tenant_id, dados)


@router.delete("/tenants/{tenant_id}/assinatura", status_code=204)
async def cancelar_assinatura_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db_admin),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    await crud_admin.cancelar_assinatura_tenant(db, tenant_id)


# ==========================================
# GESTÃO DE ACESSOS — cross-tenant (qualquer escola)
# ==========================================
# Mesmo crud usado por app/api/v1/usuarios.py (Gestor, só a própria
# escola) — aqui o tenant_id vem do path da URL em vez do token, é a
# única diferença.

@router.get("/tenants/{tenant_id}/usuarios")
async def listar_usuarios_do_tenant(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA)
):
    """Staff (Gestor/Secretaria/Professor) de uma escola específica."""
    return await crud_usuarios.listar_usuarios(db, tenant_id, page, page_size)


@router.post("/tenants/{tenant_id}/usuarios/secretaria", status_code=201)
async def criar_secretaria_no_tenant(
    tenant_id: uuid.UUID, dados: SecretariaCreate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Cria uma conta de Secretaria numa escola específica (ex.: apoio ao onboarding)."""
    novo = await crud_usuarios.criar_secretaria(db, tenant_id, dados, utilizador["usuario_id"])
    return {"mensagem": f'Conta de Secretaria criada para "{novo.nome_completo}".', "id": novo.id}


@router.patch("/tenants/{tenant_id}/usuarios/{usuario_id}/perfil")
async def alterar_perfil_no_tenant(
    tenant_id: uuid.UUID, usuario_id: uuid.UUID, dados: PerfilAcessoUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Muda o perfil (Gestor/Secretaria) de um utilizador de qualquer escola."""
    alterado = await crud_usuarios.alterar_perfil(db, tenant_id, usuario_id, dados, utilizador["usuario_id"])
    return {"mensagem": f'"{alterado.nome_completo}" passou a ter o perfil {alterado.perfil_acesso}.', "perfil_acesso": alterado.perfil_acesso}


@router.patch("/tenants/{tenant_id}/usuarios/{usuario_id}/ativo")
async def alterar_estado_ativo_no_tenant(
    tenant_id: uuid.UUID, usuario_id: uuid.UUID, dados: AtivoUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Suspende ou reativa o acesso de UM utilizador de qualquer escola."""
    alterado = await crud_usuarios.alterar_estado_ativo(db, tenant_id, usuario_id, dados.ativo, utilizador["usuario_id"])
    return {"mensagem": f'"{alterado.nome_completo}" agora está {"ativo" if alterado.ativo else "suspenso"}.', "ativo": alterado.ativo}


@router.post("/tenants/{tenant_id}/usuarios/{usuario_id}/dois-fatores/desativar")
async def desativar_dois_fatores_no_tenant(
    tenant_id: uuid.UUID, usuario_id: uuid.UUID,
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA)
):
    """Desliga a verificação em dois passos de um utilizador de qualquer escola
    (ex.: o único Gestor de uma escola perdeu o acesso ao e-mail)."""
    alterado = await crud_usuarios.desativar_dois_fatores(db, tenant_id, usuario_id, utilizador["usuario_id"])
    return {"mensagem": f'Verificação em dois passos de "{alterado.nome_completo}" desativada.', "dois_fatores_ativo": alterado.dois_fatores_ativo}


@router.get("/tenants/{tenant_id}/usuarios/auditoria")
async def listar_auditoria_do_tenant(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Histórico de gestão de acessos de uma escola específica."""
    return await crud_usuarios.listar_auditoria(db, tenant_id, page, page_size)


# ==========================================
# AUDITORIA GERAL — cross-tenant (qualquer escola)
# ==========================================
# Mesmo crud usado por app/api/v1/auditoria.py (Gestor, só a própria
# escola) — aqui o tenant_id vem do path da URL em vez do token.

@router.get("/tenants/{tenant_id}/auditoria")
async def listar_auditoria_geral_do_tenant(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    entidade: str | None = Query(None), entidade_id: str | None = Query(None),
    acao: str | None = Query(None), autor_id: uuid.UUID | None = Query(None),
    data_inicio: date | None = Query(None), data_fim: date | None = Query(None),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Trilha de auditoria geral (quem criou/alterou o quê) de uma escola específica."""
    return await crud_auditoria.listar(
        db, tenant_id, page, page_size, entidade, entidade_id, acao, autor_id, data_inicio, data_fim
    )


@router.get("/tenants/{tenant_id}/auditoria/entidades")
async def listar_entidades_auditoria_do_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_auditoria.listar_entidades_distintas(db, tenant_id)


# ==========================================
# TICKETS DE SUPORTE — cross-tenant (qualquer escola, incluindo
# visitantes sem tenant nenhum — ver models_suporte.py::TicketSuporte)
# ==========================================

@router.get("/tickets")
async def listar_tickets(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA)
):
    return await crud_suporte.listar_tickets_admin(db, page, page_size, estado)


@router.get("/tickets/{ticket_id}", response_model=TicketAdminComMensagens)
async def obter_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA)
):
    return await crud_suporte.obter_ticket_admin_detalhe(db, ticket_id)


@router.post("/tickets/{ticket_id}/mensagens", status_code=201)
async def responder_ticket(
    ticket_id: uuid.UUID, dados: MensagemTicketCreate,
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA)
):
    """Responde ao ticket; se for de um visitante sem conta (tenant_id None), a resposta é também enviada por e-mail."""
    await crud_suporte.responder_ticket_admin(db, ticket_id, dados)
    return {"mensagem": "Resposta enviada."}


@router.patch("/tickets/{ticket_id}/estado")
async def alterar_estado_ticket(
    ticket_id: uuid.UUID, dados: TicketEstadoUpdate,
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA)
):
    ticket = await crud_suporte.atualizar_estado_admin(db, ticket_id, dados.estado)
    return {"mensagem": f"Ticket marcado como {ticket.estado}.", "estado": ticket.estado}


# ==========================================
# ESTATÍSTICAS — cross-tenant (qualquer escola)
# ==========================================
# Mesmos cruds de app/api/v1/estatisticas.py (Gestor/Secretaria, só a
# própria escola) — aqui o tenant_id vem do path da URL em vez do
# token, é a única diferença: obter_dashboard/obter_relatorio já
# filtram tudo explicitamente por tenant_id, nunca dependeram do RLS
# (que aqui está desligado de propósito, como em todo este ficheiro).
# O Super Admin escolhe a escola primeiro (GET /tenants acima) e só
# depois pede as estatísticas dela — ver features/admin/estatisticas.component.

@router.get("/tenants/{tenant_id}/estatisticas/dashboard")
async def obter_dashboard_do_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_estatisticas.obter_dashboard(db, tenant_id)


@router.get("/tenants/{tenant_id}/estatisticas/relatorio")
async def obter_relatorio_do_tenant(
    tenant_id: uuid.UUID,
    data_inicio: date = Query(...), data_fim: date = Query(...),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_estatisticas.obter_relatorio(db, tenant_id, data_inicio, data_fim)


@router.get("/tenants/{tenant_id}/estatisticas/relatorio.xlsx")
async def exportar_relatorio_xlsx_do_tenant(
    tenant_id: uuid.UUID,
    data_inicio: date = Query(...), data_fim: date = Query(...),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    relatorio = await crud_estatisticas.obter_relatorio(db, tenant_id, data_inicio, data_fim)
    conteudo = estatisticas_excel.gerar_xlsx(relatorio)
    return Response(
        content=conteudo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="estatisticas-{data_inicio}-a-{data_fim}.xlsx"'}
    )


@router.get("/tenants/{tenant_id}/estatisticas/relatorio.xls")
async def exportar_relatorio_xls_do_tenant(
    tenant_id: uuid.UUID,
    data_inicio: date = Query(...), data_fim: date = Query(...),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Formato binário pré-2007 — mantido só para quem precise mesmo dele; .xlsx acima é o formato recomendado."""
    relatorio = await crud_estatisticas.obter_relatorio(db, tenant_id, data_inicio, data_fim)
    conteudo = estatisticas_excel.gerar_xls(relatorio)
    return Response(
        content=conteudo, media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f'attachment; filename="estatisticas-{data_inicio}-a-{data_fim}.xls"'}
    )


# ==========================================
# DESPESAS — cross-tenant (qualquer escola)
# ==========================================
# Pré-requisito de Estatísticas ("maiores saídas") — mesmo crud de
# app/api/v1/financeiro.py, tenant_id do path em vez do token.

@router.get("/tenants/{tenant_id}/despesas")
async def listar_despesas_do_tenant(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    data_inicio: date | None = Query(None), data_fim: date | None = Query(None),
    categoria: str | None = Query(None),
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    return await crud_financeiro.listar_despesas(db, tenant_id, page, page_size, data_inicio, data_fim, categoria)


@router.post("/tenants/{tenant_id}/despesas", status_code=201)
async def criar_despesa_no_tenant(
    tenant_id: uuid.UUID, dados: DespesaCreate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    """Lançada em nome do próprio Super Admin (utilizador["usuario_id"]) — não pertence à escola, mas o FK de criado_por é global."""
    return await crud_financeiro.criar_despesa(db, tenant_id, utilizador["usuario_id"], dados)


@router.delete("/tenants/{tenant_id}/despesas/{despesa_id}", status_code=204)
async def remover_despesa_do_tenant(
    tenant_id: uuid.UUID, despesa_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)
):
    await crud_financeiro.remover_despesa(db, tenant_id, despesa_id)


# ==========================================
# SEGURANÇA — tentativas de acesso indevido em todas as escolas (incluindo
# as anónimas) e IPs bloqueados automaticamente (ver app/core/eventos_seguranca.py).
# ==========================================
@router.get("/seguranca/eventos", response_model=PaginaOut[EventoSegurancaOut])
async def listar_eventos_seguranca(
    tenant_id: uuid.UUID | None = None,
    tipo: str | None = Query(None, max_length=40), gravidade: str | None = Query(None, max_length=10),
    ip: str | None = Query(None, max_length=45),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(_sessao_equipa), utilizador: dict = Depends(_EQUIPA),
):
    return await crud_seguranca.listar_eventos(
        db, tenant_id=tenant_id, so_da_escola=False, tipo=tipo, gravidade=gravidade, ip=ip,
        page=page, page_size=page_size,
    )


@router.get("/seguranca/bloqueios", response_model=list[BloqueioIpOut])
async def listar_ips_bloqueados(utilizador: dict = Depends(_EQUIPA)):
    return await crud_seguranca.listar_bloqueios()


@router.delete("/seguranca/bloqueios/{ip}")
async def desbloquear_ip(ip: str, utilizador: dict = Depends(_EQUIPA)):
    """Levanta já o bloqueio (ex.: era a rede de uma escola, não um ataque)."""
    await eventos_seguranca.desbloquear_ip(ip)
    return {"mensagem": f"O endereço {ip} foi desbloqueado."}



# ==========================================
# EQUIPA DA PLATAFORMA — contas de Suporte (só o Super Admin).
# ==========================================
@router.get("/equipa", response_model=list[MembroEquipaOut])
async def listar_equipa(db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER)):
    return await crud_admin.listar_equipa(db, utilizador["tenant_id"])


@router.post("/equipa", response_model=MembroEquipaOut, status_code=201)
async def criar_membro_suporte(
    dados: MembroEquipaCreate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER),
):
    membro = await crud_admin.criar_membro_suporte(db, utilizador["tenant_id"], dados.nome_completo, dados.email, dados.palavra_passe)
    return await _membro_out(membro)


@router.patch("/equipa/{usuario_id}/ativo", response_model=MembroEquipaOut)
async def alterar_estado_membro(
    usuario_id: uuid.UUID, dados: AtivoUpdate,
    db: AsyncSession = Depends(obter_sessao_db_admin), utilizador: dict = Depends(_PODE_ACEDER),
):
    return await _membro_out(await crud_admin.alterar_estado_membro(db, utilizador["tenant_id"], usuario_id, dados.ativo))


async def _membro_out(membro) -> dict:
    return {"id": membro.id, "nome_completo": membro.nome_completo, "email": membro.email,
            "perfil_acesso": membro.perfil_acesso, "ativo": membro.ativo, "data_criacao": membro.data_criacao}
