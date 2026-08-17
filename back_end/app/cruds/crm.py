"""Acesso a dados e regras de negócio (RN01, RN03) do CRM."""
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database.models import Tenant
from app.database.models_academico import Curso, Turma
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, AlunoResponsavel, ResponsavelFinanceiroLegal
from app.database.models_crm import FunilEtapa, LeadCandidato, OportunidadeCRM
from app.schemas.crm import EtapaCreate, LeadPublicoCreate, LeadStaffCreate, LeadUpdate, OportunidadeCreate, OportunidadeUpdate
from app.schemas.matriculas import MatriculaCreate
from app.schemas.financeiro import ContratoCreate
from app.cruds import matriculas as matriculas_crud
from app.cruds import financeiro as financeiro_crud

ORIGENS_VALIDAS = {"SITE", "FACEBOOK", "INDICACAO", "PRESENCIAL", "OUTRO"}

# Etapas por omissão criadas na primeira vez que uma escola acede ao
# funil (ver garantir_funil_seed) — nomes tirados literalmente do
# exemplo do documento de arquitetura. A última é a etapa "eh_etapa_ganho".
ETAPAS_PADRAO = [
    (1, "Nova Lead", False),
    (2, "Visita Agendada", False),
    (3, "Documentação Pendente", False),
    (4, "Matriculado", True),
]


# ==========================================
# HELPERS
# ==========================================
async def garantir_funil_seed(db: AsyncSession, tenant_id) -> list[FunilEtapa]:
    """Cria as etapas por omissão na primeira vez que a escola usa o CRM."""
    existentes = (await db.execute(
        select(FunilEtapa).where(FunilEtapa.tenant_id == tenant_id).order_by(FunilEtapa.ordem)
    )).scalars().all()
    if existentes:
        return list(existentes)

    novas = [
        FunilEtapa(tenant_id=tenant_id, ordem=ordem, nome_etapa=nome, eh_etapa_ganho=ganho)
        for ordem, nome, ganho in ETAPAS_PADRAO
    ]
    db.add_all(novas)
    await db.commit()
    for etapa in novas:
        await db.refresh(etapa)
    return novas


def _gerar_matricula_interna(lead_id: uuid.UUID) -> str:
    return f"LEAD-{str(lead_id).split('-')[0].upper()}"


async def _converter_lead_em_aluno(db: AsyncSession, tenant_id, oportunidade: OportunidadeCRM, lead: LeadCandidato) -> None:
    """
    RN01 — Automação de Conversão: quando a Oportunidade entra numa
    etapa eh_etapa_ganho, gera o Responsável e o Aluno automaticamente.

    O documento também prevê gerar logo o Contrato_Financeiro, mas isso
    exige uma Matricula (turma) já atribuída — e por omissão o CRM não
    sabe para que turma vai este aluno (só sabe o Curso de interesse).
    Esta função trata só de Responsável + Aluno + vínculo; se a
    Secretaria já tiver preenchido turma_interesse_id na Oportunidade
    (ver OportunidadeUpdate), _tentar_matricula_e_contrato_automaticos
    (chamada a seguir, em mover_oportunidade) completa também a
    Matrícula e o Contrato Financeiro, reaproveitando os cruds dos
    módulos já existentes (Nível 1 e Nível 2) em vez de duplicar essa
    lógica aqui. Sem turma definida, a Secretaria conclui à mão.
    """
    if oportunidade.aluno_gerado_id:
        return  # idempotência — já convertido antes

    if not lead.data_nascimento_candidato:
        raise HTTPException(
            status_code=400,
            detail="Preencha a data de nascimento do candidato antes de o mover para esta etapa."
        )

    novo_responsavel = ResponsavelFinanceiroLegal(
        tenant_id=tenant_id,
        nome_completo=lead.nome_responsavel,
        telefone_contato=lead.telefone or "",
        email=lead.email_contato,
    )
    db.add(novo_responsavel)
    await db.flush()

    novo_aluno = Aluno(
        tenant_id=tenant_id,
        matricula_interna=_gerar_matricula_interna(lead.id),
        nome_completo=lead.nome_aluno_candidato,
        data_nascimento=lead.data_nascimento_candidato,
    )
    db.add(novo_aluno)
    await db.flush()

    db.add(AlunoResponsavel(
        tenant_id=tenant_id,
        aluno_id=novo_aluno.id,
        responsavel_id=novo_responsavel.id,
        tipo_parentesco="Responsável",
        responsavel_financeiro=True,
    ))

    oportunidade.aluno_gerado_id = novo_aluno.id
    oportunidade.responsavel_gerado_id = novo_responsavel.id


async def _tentar_matricula_e_contrato_automaticos(db: AsyncSession, tenant_id, oportunidade: OportunidadeCRM) -> str | None:
    """
    Extensão da RN01: se a Oportunidade já tem Turma pretendida
    (turma_interesse_id) e o Aluno já foi gerado, tenta completar
    também a Matrícula e — havendo valor_estimado_anual — o Contrato
    Financeiro, reaproveitando os cruds de Matrículas/Financeiro tal
    como um funcionário faria manualmente.

    Chamada depois de a etapa já ter sido movida e commitada (ver
    mover_oportunidade) — por isso nunca bloqueia o avanço do funil:
    se algo aqui falhar (turma entretanto lotada, valor inválido...) a
    Oportunidade já está na nova etapa na mesma, e só fica um aviso na
    mensagem devolvida para a Secretaria concluir à mão o que faltar.
    Também é idempotente: se já existir Matrícula/Contrato de uma
    tentativa anterior, não duplica.
    """
    if not oportunidade.turma_interesse_id or not oportunidade.aluno_gerado_id:
        return None

    turma = (await db.execute(
        select(Turma).where(Turma.id == oportunidade.turma_interesse_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    if not turma:
        return None  # turma pode ter sido apagada/desvinculada entretanto

    try:
        matricula = await matriculas_crud.criar_matricula(
            db, tenant_id,
            MatriculaCreate(aluno_id=oportunidade.aluno_gerado_id, turma_id=turma.id, ano_letivo=turma.ano_letivo)
        )
    except HTTPException as erro:
        if erro.status_code == 400 and "já está matriculado" in erro.detail:
            # Idempotência: tentativa anterior já matriculou — usa essa Matrícula para tentar o contrato.
            matricula = (await db.execute(
                select(Matricula).where(
                    Matricula.aluno_id == oportunidade.aluno_gerado_id,
                    Matricula.turma_id == turma.id,
                    Matricula.ano_letivo == turma.ano_letivo,
                )
            )).scalars().first()
        else:
            return f"Matrícula automática falhou ({erro.detail}) — conclua manualmente em Matrículas."

    if not matricula:
        return None

    if not oportunidade.valor_estimado_anual or not oportunidade.responsavel_gerado_id:
        return "Matrícula criada automaticamente — defina o valor anual da oportunidade para também gerar o contrato financeiro."

    try:
        await financeiro_crud.criar_contrato(db, tenant_id, ContratoCreate(
            matricula_id=matricula.id,
            responsavel_id=oportunidade.responsavel_gerado_id,
            valor_total_anual=oportunidade.valor_estimado_anual,
        ))
    except HTTPException as erro:
        if erro.status_code == 400 and "Já existe um contrato" in erro.detail:
            return "Matrícula e contrato financeiro já existiam — nada a fazer."
        return f"Matrícula criada, mas o contrato financeiro automático falhou ({erro.detail}) — conclua manualmente em Financeiro."

    return "Matrícula e contrato financeiro criados automaticamente."


# ==========================================
# A. CAPTAÇÃO PÚBLICA (RN03) — sem autenticação
# ==========================================
async def criar_lead_publico(db: AsyncSession, tenant_id: uuid.UUID, dados: LeadPublicoCreate) -> None:
    """
    Endpoint público para a escola incorporar um formulário no seu
    próprio site (RN03). Sem token — qualquer visitante pode chamar
    isto, por isso só cria um Lead + Oportunidade (nunca escreve nas
    tabelas académicas/financeiras diretamente).
    """
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant or tenant.status != "ATIVO":
        raise HTTPException(status_code=404, detail="Escola não encontrada.")

    if dados.origem_lead not in ORIGENS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Origem inválida. Use uma de: {', '.join(sorted(ORIGENS_VALIDAS))}.")

    await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(tenant_id)})

    if dados.curso_interesse_id:
        curso = (await db.execute(
            select(Curso).where(Curso.id == dados.curso_interesse_id, Curso.tenant_id == tenant_id)
        )).scalars().first()
        if not curso:
            raise HTTPException(status_code=400, detail="Curso de interesse não encontrado nesta escola.")

    etapas = await garantir_funil_seed(db, tenant_id)
    primeira_etapa = min(etapas, key=lambda e: e.ordem)

    novo_lead = LeadCandidato(
        tenant_id=tenant_id,
        nome_responsavel=dados.nome_responsavel,
        email_contato=dados.email_contato,
        telefone=dados.telefone,
        nome_aluno_candidato=dados.nome_aluno_candidato,
        curso_interesse_id=dados.curso_interesse_id,
        origem_lead=dados.origem_lead,
    )
    db.add(novo_lead)
    await db.flush()

    nova_oportunidade = OportunidadeCRM(
        tenant_id=tenant_id,
        lead_id=novo_lead.id,
        etapa_id=primeira_etapa.id,
    )
    db.add(nova_oportunidade)
    await db.commit()


# ==========================================
# B. FUNIL (Kanban)
# ==========================================
async def listar_funil(db: AsyncSession, tenant_id) -> list[FunilEtapa]:
    etapas = await garantir_funil_seed(db, tenant_id)
    return sorted(etapas, key=lambda e: e.ordem)


async def criar_etapa(db: AsyncSession, tenant_id, dados: EtapaCreate) -> FunilEtapa:
    await garantir_funil_seed(db, tenant_id)  # garante que já há uma base antes de adicionar mais

    nova_etapa = FunilEtapa(tenant_id=tenant_id, ordem=dados.ordem, nome_etapa=dados.nome_etapa, eh_etapa_ganho=dados.eh_etapa_ganho)
    db.add(nova_etapa)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma etapa nessa posição (ordem) — escolha outra.")
    await db.refresh(nova_etapa)
    return nova_etapa


# ==========================================
# C. LEADS
# ==========================================
async def listar_leads(db: AsyncSession, tenant_id) -> list[LeadCandidato]:
    leads = (await db.execute(
        select(LeadCandidato).where(LeadCandidato.tenant_id == tenant_id)
        .order_by(LeadCandidato.data_entrada.desc())
    )).scalars().all()
    return leads


async def criar_lead_manual(db: AsyncSession, tenant_id, dados: LeadStaffCreate) -> tuple[LeadCandidato, uuid.UUID]:
    """Regista um Lead diretamente pela Secretaria (ex: telefonema, visita) e já o coloca na 1ª etapa do funil."""
    if dados.origem_lead not in ORIGENS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Origem inválida. Use uma de: {', '.join(sorted(ORIGENS_VALIDAS))}.")

    if dados.curso_interesse_id:
        curso = (await db.execute(
            select(Curso).where(Curso.id == dados.curso_interesse_id, Curso.tenant_id == tenant_id)
        )).scalars().first()
        if not curso:
            raise HTTPException(status_code=400, detail="Curso de interesse não encontrado na sua instituição.")

    etapas = await garantir_funil_seed(db, tenant_id)
    primeira_etapa = min(etapas, key=lambda e: e.ordem)

    novo_lead = LeadCandidato(
        tenant_id=tenant_id,
        nome_responsavel=dados.nome_responsavel,
        email_contato=dados.email_contato,
        telefone=dados.telefone,
        nome_aluno_candidato=dados.nome_aluno_candidato,
        data_nascimento_candidato=dados.data_nascimento_candidato,
        curso_interesse_id=dados.curso_interesse_id,
        origem_lead=dados.origem_lead,
    )
    db.add(novo_lead)
    await db.flush()

    nova_oportunidade = OportunidadeCRM(tenant_id=tenant_id, lead_id=novo_lead.id, etapa_id=primeira_etapa.id)
    db.add(nova_oportunidade)
    await db.commit()
    await db.refresh(novo_lead)
    await db.refresh(nova_oportunidade)

    return novo_lead, nova_oportunidade.id


async def atualizar_lead(db: AsyncSession, tenant_id, lead_id: uuid.UUID, dados: LeadUpdate) -> LeadCandidato:
    """Completa/corrige os dados do Lead — em particular a data de nascimento, exigida antes da conversão (RN01)."""
    lead = (await db.execute(
        select(LeadCandidato).where(LeadCandidato.id == lead_id, LeadCandidato.tenant_id == tenant_id)
    )).scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado na sua instituição.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(lead, campo, valor)

    await db.commit()
    await db.refresh(lead)
    return lead


# ==========================================
# D. OPORTUNIDADES
# ==========================================
async def listar_oportunidades(db: AsyncSession, tenant_id, etapa_id: uuid.UUID | None = None) -> list[dict]:
    """Lista as oportunidades já com os dados do Lead, para montar o quadro Kanban."""
    query = (
        select(OportunidadeCRM, LeadCandidato)
        .join(LeadCandidato, LeadCandidato.id == OportunidadeCRM.lead_id)
        .where(OportunidadeCRM.tenant_id == tenant_id)
    )
    if etapa_id:
        query = query.where(OportunidadeCRM.etapa_id == etapa_id)

    resultado = await db.execute(query.order_by(OportunidadeCRM.data_criacao))
    return [
        {
            "id": oportunidade.id,
            "etapa_id": oportunidade.etapa_id,
            "valor_estimado_anual": oportunidade.valor_estimado_anual,
            "data_fecho_prevista": oportunidade.data_fecho_prevista,
            "turma_interesse_id": oportunidade.turma_interesse_id,
            "aluno_gerado_id": oportunidade.aluno_gerado_id,
            "data_criacao": oportunidade.data_criacao,
            "lead": {
                "id": lead.id,
                "nome_responsavel": lead.nome_responsavel,
                "email_contato": lead.email_contato,
                "telefone": lead.telefone,
                "nome_aluno_candidato": lead.nome_aluno_candidato,
                "data_nascimento_candidato": lead.data_nascimento_candidato,
                "origem_lead": lead.origem_lead,
                "curso_interesse_id": lead.curso_interesse_id,
                "data_entrada": lead.data_entrada,
            },
        }
        for oportunidade, lead in resultado.all()
    ]


async def criar_oportunidade(db: AsyncSession, tenant_id, dados: OportunidadeCreate) -> OportunidadeCRM:
    """Cria manualmente uma oportunidade para um Lead já existente (ex: contacto presencial), na 1ª etapa do funil."""
    lead = (await db.execute(
        select(LeadCandidato).where(LeadCandidato.id == dados.lead_id, LeadCandidato.tenant_id == tenant_id)
    )).scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado na sua instituição.")

    if dados.turma_interesse_id:
        turma = (await db.execute(
            select(Turma).where(Turma.id == dados.turma_interesse_id, Turma.tenant_id == tenant_id)
        )).scalars().first()
        if not turma:
            raise HTTPException(status_code=400, detail="Turma pretendida não encontrada na sua instituição.")

    etapas = await garantir_funil_seed(db, tenant_id)
    primeira_etapa = min(etapas, key=lambda e: e.ordem)

    nova_oportunidade = OportunidadeCRM(
        tenant_id=tenant_id,
        lead_id=dados.lead_id,
        etapa_id=primeira_etapa.id,
        valor_estimado_anual=dados.valor_estimado_anual,
        data_fecho_prevista=dados.data_fecho_prevista,
        turma_interesse_id=dados.turma_interesse_id,
    )
    db.add(nova_oportunidade)
    await db.commit()
    await db.refresh(nova_oportunidade)
    return nova_oportunidade


async def atualizar_oportunidade(db: AsyncSession, tenant_id, oportunidade_id: uuid.UUID, dados: OportunidadeUpdate) -> tuple[OportunidadeCRM, str]:
    """
    Completa/corrige a oportunidade — em particular a Turma pretendida,
    que a RN01 precisa para gerar Matrícula + Contrato automaticamente.

    Se a oportunidade já tiver sido convertida antes (aluno_gerado_id já
    definido, ex: só faltava a turma na altura em que ganhou o funil),
    esta função já tenta a automação de imediato — sem isto, a
    Secretaria teria de mover o cartão para fora e para dentro da etapa
    de novo só para acionar o mesmo código em mover_oportunidade.
    """
    oportunidade = (await db.execute(
        select(OportunidadeCRM).where(OportunidadeCRM.id == oportunidade_id, OportunidadeCRM.tenant_id == tenant_id)
    )).scalars().first()
    if not oportunidade:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada na sua instituição.")

    dados_definidos = dados.model_dump(exclude_unset=True)
    if "turma_interesse_id" in dados_definidos and dados_definidos["turma_interesse_id"]:
        turma = (await db.execute(
            select(Turma).where(Turma.id == dados_definidos["turma_interesse_id"], Turma.tenant_id == tenant_id)
        )).scalars().first()
        if not turma:
            raise HTTPException(status_code=400, detail="Turma pretendida não encontrada na sua instituição.")

    for campo, valor in dados_definidos.items():
        setattr(oportunidade, campo, valor)

    await db.commit()
    await db.refresh(oportunidade)

    mensagem = "Oportunidade atualizada."
    if oportunidade.aluno_gerado_id:
        aviso_automacao = await _tentar_matricula_e_contrato_automaticos(db, tenant_id, oportunidade)
        if aviso_automacao:
            mensagem += " " + aviso_automacao

    return oportunidade, mensagem


async def mover_oportunidade(db: AsyncSession, tenant_id, oportunidade_id: uuid.UUID, nova_etapa_id: uuid.UUID) -> tuple[OportunidadeCRM, str]:
    """Move o cartão para outra etapa. Se a etapa de destino for eh_etapa_ganho, aciona a RN01. Devolve (oportunidade, mensagem)."""
    oportunidade = (await db.execute(
        select(OportunidadeCRM).where(OportunidadeCRM.id == oportunidade_id, OportunidadeCRM.tenant_id == tenant_id)
    )).scalars().first()
    if not oportunidade:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada na sua instituição.")

    nova_etapa = (await db.execute(
        select(FunilEtapa).where(FunilEtapa.id == nova_etapa_id, FunilEtapa.tenant_id == tenant_id)
    )).scalars().first()
    if not nova_etapa:
        raise HTTPException(status_code=404, detail="Etapa não encontrada na sua instituição.")

    lead = (await db.execute(
        select(LeadCandidato).where(LeadCandidato.id == oportunidade.lead_id)
    )).scalars().first()

    # A conversão (que pode falhar com 400 se faltar a data de
    # nascimento) corre antes de mexer na etapa — assim, se falhar, a
    # oportunidade fica exatamente onde estava, sem mudança parcial.
    if nova_etapa.eh_etapa_ganho:
        await _converter_lead_em_aluno(db, tenant_id, oportunidade, lead)

    oportunidade.etapa_id = nova_etapa.id
    await db.commit()
    await db.refresh(oportunidade)

    mensagem = "Oportunidade movida com sucesso."
    if nova_etapa.eh_etapa_ganho and oportunidade.aluno_gerado_id:
        # Corre depois de commitada a mudança de etapa — nunca a bloqueia
        # (ver docstring de _tentar_matricula_e_contrato_automaticos).
        aviso_automacao = await _tentar_matricula_e_contrato_automaticos(db, tenant_id, oportunidade)
        mensagem += " " + (
            aviso_automacao or
            "Aluno e responsável criados — indique a Turma pretendida para também gerar a matrícula e o contrato financeiro automaticamente."
        )

    return oportunidade, mensagem
