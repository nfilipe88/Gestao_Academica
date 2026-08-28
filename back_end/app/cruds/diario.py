"""Acesso a dados e regras de negócio (RN01-RN04) do Diário de Classe."""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, tuple_
from datetime import date
from decimal import Decimal
import uuid

from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_pessoas import Aluno, Professor
from app.database.models_matricula import Matricula
from app.database.models_diario import (
    Avaliacao, NotaAvaliacao, PeriodoAvaliacao, ProfessorTurmaDisciplina,
    RegistroFrequencia, RegistroNota, RegistroNotaAuditoria, TipoAvaliacaoConfig
)
from app.schemas.diario import (
    AvaliacaoCreate, AvaliacaoUpdate, FrequenciaLoteCreate, NotaAvaliacaoLoteCreate, NotaLoteCreate, PeriodoAvaliacaoCreate
)

NOTA_MINIMA = Decimal("0.0")
NOTA_MAXIMA = Decimal("10.0")


# ==========================================
# VALIDAÇÕES PARTILHADAS
# ==========================================
async def _validar_turma_disciplina(db: AsyncSession, tenant_id, turma_id: uuid.UUID, disciplina_id: uuid.UUID):
    turma = (await db.execute(
        select(Turma).where(Turma.id == turma_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")


async def _validar_autoria(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID):
    """
    RN01 - Validação de Autoria: Gestor/Secretaria têm acesso administrativo
    a qualquer turma. Um Professor só pode lançar/consultar o diário das
    turmas+disciplinas às quais está efetivamente alocado.
    """
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return

    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para aceder ao Diário de Classe.")

    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"],
            Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=403, detail="Utilizador não corresponde a nenhum professor cadastrado.")

    alocado = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.professor_id == professor.id,
            ProfessorTurmaDisciplina.turma_id == turma_id,
            ProfessorTurmaDisciplina.disciplina_id == disciplina_id
        )
    )).scalars().first()
    if not alocado:
        raise HTTPException(status_code=403, detail="Não lecciona esta disciplina nesta turma.")


async def _validar_periodo_aberto(db: AsyncSession, tenant_id, nome_periodo: str):
    """
    RN03 - Janela de Lançamento: só bloqueia se a secretaria tiver
    criado (e trancado) um registo para este nome de período. Um nome
    sem registo correspondente continua livre — a gestão de períodos é
    opcional, não um pré-requisito para lançar notas.
    """
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id, PeriodoAvaliacao.nome == nome_periodo)
    )).scalars().first()
    if periodo and not periodo.aberto:
        raise HTTPException(
            status_code=403,
            detail=f"O período de avaliação \"{nome_periodo}\" está trancado pela secretaria — já não é possível lançar/alterar notas."
        )


async def _validar_sem_avaliacoes(db: AsyncSession, turma_id: uuid.UUID, disciplina_id: uuid.UUID, periodo_avaliacao: str):
    """
    Bloqueia o lançamento manual direto da nota final (lancar_notas_lote)
    assim que exista pelo menos uma Avaliacao (prova/contínua) criada
    para esta turma+disciplina+período — a partir desse momento a nota
    final passa a ser calculada automaticamente a partir delas (ver
    _recalcular_nota_periodo) e só se edita lançando notas nas
    avaliações, não escrevendo aqui.
    """
    existe = (await db.execute(
        select(Avaliacao.id).where(
            Avaliacao.turma_id == turma_id,
            Avaliacao.disciplina_id == disciplina_id,
            Avaliacao.periodo_avaliacao == periodo_avaliacao
        ).limit(1)
    )).scalars().first()
    if existe:
        raise HTTPException(
            status_code=400,
            detail=f'Já existem avaliações criadas para "{periodo_avaliacao}" nesta disciplina — a nota final é calculada automaticamente a partir delas. Lance as notas em cada avaliação em vez de escrever a nota final diretamente.'
        )


# ==========================================
# A. CARREGAR A GRADE (Lista de Alunos da Turma)
# ==========================================
async def listar_alunos_da_turma_disciplina(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID) -> list[dict]:
    """Lista os alunos matriculados (ATIVO) para montar a tabela de chamada/notas."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    resultado = await db.execute(
        select(Matricula.id, Aluno.nome_completo, Aluno.matricula_interna)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(
            Matricula.turma_id == turma_id,
            Matricula.status_matricula == "ATIVO",
            Matricula.tenant_id == tenant_id
        )
        .order_by(Aluno.nome_completo)
    )
    return [
        {
            "matricula_id": matricula_id,
            "nome_aluno": nome_aluno,
            "matricula_interna": matricula_interna,
            "numero_chamada": indice + 1,
        }
        for indice, (matricula_id, nome_aluno, matricula_interna) in enumerate(resultado.all())
    ]


# ==========================================
# B. LANÇAMENTO DE FREQUÊNCIA EM LOTE (Chamada)
# ==========================================
async def lancar_frequencias_lote(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, dados: FrequenciaLoteCreate) -> int:
    """Recebe a presença/faltas de toda a turma para uma aula, numa única chamada. Devolve o total processado."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    matriculas_da_turma = set((await db.execute(
        select(Matricula.id).where(Matricula.turma_id == turma_id, Matricula.tenant_id == tenant_id)
    )).scalars().all())

    # Uma só query para todos os registos já existentes desta aula, em
    # vez de um SELECT por aluno dentro do loop (uma turma típica é
    # 20-40 alunos, e isto corre a cada chamada — a operação mais
    # frequente do Diário de Classe, multiplicada por todas as turmas/
    # disciplinas/dias, em todas as escolas).
    existentes_da_aula = {
        r.matricula_id: r
        for r in (await db.execute(
            select(RegistroFrequencia).where(
                RegistroFrequencia.disciplina_id == disciplina_id,
                RegistroFrequencia.data_aula == dados.data_aula,
                RegistroFrequencia.matricula_id.in_(matriculas_da_turma),
            )
        )).scalars().all()
    }

    total = 0
    for item in dados.frequencias:
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = existentes_da_aula.get(item.matricula_id)

        if existente:
            # Upsert: relançar a chamada do mesmo dia atualiza, não duplica.
            existente.presenca = item.presenca
            existente.faltas = item.faltas
            existente.quantidade_aulas = dados.quantidade_aulas
            existente.conteudo_programado = dados.conteudo_programado
        else:
            nova = RegistroFrequencia(
                tenant_id=tenant_id,
                matricula_id=item.matricula_id,
                disciplina_id=disciplina_id,
                data_aula=dados.data_aula,
                quantidade_aulas=dados.quantidade_aulas,
                conteudo_programado=dados.conteudo_programado,
                presenca=item.presenca,
                faltas=item.faltas
            )
            db.add(nova)
            # Mesmo matricula_id duas vezes no mesmo lote (não deveria
            # acontecer, mas o dicionário só foi construído uma vez
            # antes do loop) — regista aqui para a segunda ocorrência
            # atualizar em vez de duplicar.
            existentes_da_aula[item.matricula_id] = nova
        total += 1

    await db.commit()
    return total


# ==========================================
# C. LANÇAMENTO DE NOTAS EM LOTE
# ==========================================
async def lancar_notas_lote(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, dados: NotaLoteCreate) -> int:
    """
    Upsert das notas de toda a turma para um período de avaliação.
    RN02: valor_nota tem de estar entre 0.0 e 10.0.
    RN03: o período tem de estar aberto.
    RN04: se a nota já existia e o valor mudou, fica um registo de auditoria.
    Devolve o total processado.
    """
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, dados.periodo_avaliacao)
    await _validar_sem_avaliacoes(db, turma_id, disciplina_id, dados.periodo_avaliacao)

    matriculas_da_turma = set((await db.execute(
        select(Matricula.id).where(Matricula.turma_id == turma_id, Matricula.tenant_id == tenant_id)
    )).scalars().all())

    # Mesma razão de lancar_frequencias_lote acima: uma query só para
    # todos os registos já existentes deste período, em vez de um
    # SELECT por aluno dentro do loop.
    existentes_do_periodo = {
        r.matricula_id: r
        for r in (await db.execute(
            select(RegistroNota).where(
                RegistroNota.disciplina_id == disciplina_id,
                RegistroNota.periodo_avaliacao == dados.periodo_avaliacao,
                RegistroNota.matricula_id.in_(matriculas_da_turma),
            )
        )).scalars().all()
    }

    total = 0
    for item in dados.notas:
        if item.valor_nota < NOTA_MINIMA or item.valor_nota > NOTA_MAXIMA:
            raise HTTPException(
                status_code=400,
                detail=f"Nota {item.valor_nota} fora do intervalo permitido ({NOTA_MINIMA} a {NOTA_MAXIMA})."
            )
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = existentes_do_periodo.get(item.matricula_id)

        if existente:
            if existente.valor_nota != item.valor_nota:
                # RN04 - Auditoria: só regista quando o valor realmente muda.
                db.add(RegistroNotaAuditoria(
                    tenant_id=tenant_id,
                    registro_nota_id=existente.id,
                    alterado_por=utilizador["usuario_id"],
                    valor_antigo=existente.valor_nota,
                    valor_novo=item.valor_nota
                ))
                existente.valor_nota = item.valor_nota
            existente.tipo_avaliacao = dados.tipo_avaliacao
            existente.data_avaliacao = dados.data_avaliacao
        else:
            nova = RegistroNota(
                tenant_id=tenant_id,
                matricula_id=item.matricula_id,
                disciplina_id=disciplina_id,
                periodo_avaliacao=dados.periodo_avaliacao,
                tipo_avaliacao=dados.tipo_avaliacao,
                data_avaliacao=dados.data_avaliacao,
                valor_nota=item.valor_nota
            )
            db.add(nova)
            existentes_do_periodo[item.matricula_id] = nova  # ver comentário equivalente acima
        total += 1

    await db.commit()
    return total


# ==========================================
# D. VISÃO GERAL DO DESEMPENHO (Dashboard do Professor)
# ==========================================
async def consolidado_turma_disciplina(
    db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, periodo_avaliacao: str | None = None
) -> dict:
    """Média da turma, alunos abaixo da média e total de faltas — para o professor bater o olho antes do conselho de turma."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    matriculas_ids = (await db.execute(
        select(Matricula.id).where(
            Matricula.turma_id == turma_id,
            Matricula.status_matricula == "ATIVO",
            Matricula.tenant_id == tenant_id
        )
    )).scalars().all()

    query_notas = select(RegistroNota.valor_nota).where(
        RegistroNota.disciplina_id == disciplina_id,
        RegistroNota.matricula_id.in_(matriculas_ids)
    )
    if periodo_avaliacao:
        query_notas = query_notas.where(RegistroNota.periodo_avaliacao == periodo_avaliacao)
    notas = (await db.execute(query_notas)).scalars().all()

    if notas:
        media_turma = sum(notas) / len(notas)
        alunos_abaixo_da_media = sum(1 for nota in notas if nota < media_turma)
    else:
        media_turma = None
        alunos_abaixo_da_media = 0

    total_faltas = (await db.execute(
        select(func.coalesce(func.sum(RegistroFrequencia.faltas), 0)).where(
            RegistroFrequencia.disciplina_id == disciplina_id,
            RegistroFrequencia.matricula_id.in_(matriculas_ids)
        )
    )).scalar_one()

    return {
        "total_alunos": len(matriculas_ids),
        "media_turma": float(media_turma) if media_turma is not None else None,
        "alunos_abaixo_da_media": alunos_abaixo_da_media,
        "total_faltas": int(total_faltas),
    }


# ==========================================
# E. PERÍODOS DE AVALIAÇÃO (RN03 — Janela de Lançamento)
# ==========================================
async def listar_periodos_avaliacao(db: AsyncSession, tenant_id) -> list[PeriodoAvaliacao]:
    """Lista os períodos geridos pela secretaria (abertos e trancados)."""
    periodos = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id)
        .order_by(PeriodoAvaliacao.data_criacao)
    )).scalars().all()
    return periodos


async def criar_periodo_avaliacao(db: AsyncSession, tenant_id, dados: PeriodoAvaliacaoCreate) -> PeriodoAvaliacao:
    """Regista um período (ex: "1º Bimestre") como gerível — nasce aberto; usar trancar_periodo_avaliacao quando o prazo terminar."""
    novo_periodo = PeriodoAvaliacao(tenant_id=tenant_id, nome=dados.nome, aberto=True)
    db.add(novo_periodo)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um período de avaliação com este nome.")
    await db.refresh(novo_periodo)
    return novo_periodo


async def trancar_periodo_avaliacao(db: AsyncSession, tenant_id, periodo_id: uuid.UUID) -> PeriodoAvaliacao:
    """A partir de agora, lancar_notas_lote com este periodo_avaliacao levanta 403."""
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.id == periodo_id, PeriodoAvaliacao.tenant_id == tenant_id)
    )).scalars().first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período de avaliação não encontrado na sua instituição.")

    periodo.aberto = False
    periodo.data_fecho = date.today()
    await db.commit()
    return periodo


async def reabrir_periodo_avaliacao(db: AsyncSession, tenant_id, periodo_id: uuid.UUID) -> PeriodoAvaliacao:
    """Corrige um trancamento feito por engano — volta a permitir lançamentos."""
    periodo = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.id == periodo_id, PeriodoAvaliacao.tenant_id == tenant_id)
    )).scalars().first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período de avaliação não encontrado na sua instituição.")

    periodo.aberto = True
    periodo.data_fecho = None
    await db.commit()
    return periodo


# ==========================================
# F. AVALIAÇÕES (provas e contínuas) + cálculo automático da nota final
# ==========================================
async def _validar_e_obter_tipo_avaliacao(db: AsyncSession, tenant_id, tipo: str) -> TipoAvaliacaoConfig:
    config = (await db.execute(
        select(TipoAvaliacaoConfig).where(
            TipoAvaliacaoConfig.tenant_id == tenant_id, TipoAvaliacaoConfig.nome == tipo, TipoAvaliacaoConfig.ativo == True  # noqa: E712
        )
    )).scalars().first()
    if not config:
        raise HTTPException(status_code=400, detail=f'Tipo de avaliação "{tipo}" inválido ou inativo — veja os tipos disponíveis em Configurações.')
    return config


def _validar_agendamento(tipo_config: TipoAvaliacaoConfig, utilizador: dict, dados) -> None:
    """
    Tipos marcados com requer_agendamento (ex.: "Prova") só podem ser
    marcados por Gestor/Secretaria, com data e hora obrigatórias — é
    esta flag, configurável por escola em Configurações, que decide se
    uma Avaliacao é uma avaliação contínua do dia-a-dia (o professor
    continua livre) ou um evento agendado formalmente.
    """
    if not tipo_config.requer_agendamento:
        return

    if utilizador["perfil_acesso"] not in ("GESTOR", "SECRETARIA"):
        raise HTTPException(
            status_code=403,
            detail=f'"{tipo_config.nome}" exige agendamento — só o Gestor ou a Secretaria podem marcar data/hora para este tipo de avaliação.'
        )
    if not dados.data_avaliacao or not dados.hora_inicio or not dados.hora_fim:
        raise HTTPException(status_code=400, detail=f'"{tipo_config.nome}" exige data, hora de início e hora de fim.')
    if dados.hora_fim <= dados.hora_inicio:
        raise HTTPException(status_code=400, detail="A hora de fim tem de ser depois da hora de início.")


async def _validar_objetivo_aprendizagem(db: AsyncSession, tenant_id, disciplina_id: uuid.UUID, objetivo_id: uuid.UUID | None):
    """Se indicado, o objetivo tem de existir e pertencer à mesma disciplina da avaliação — não faz sentido uma prova de Matemática apontar para um objetivo de Ciências."""
    if objetivo_id is None:
        return
    objetivo = (await db.execute(
        select(ObjetivoAprendizagem).where(
            ObjetivoAprendizagem.id == objetivo_id,
            ObjetivoAprendizagem.tenant_id == tenant_id
        )
    )).scalars().first()
    if not objetivo:
        raise HTTPException(status_code=404, detail="Objetivo de aprendizagem não encontrado na sua instituição.")
    if objetivo.disciplina_id != disciplina_id:
        raise HTTPException(status_code=400, detail="Este objetivo de aprendizagem pertence a outra disciplina.")


async def _obter_avaliacao(db: AsyncSession, tenant_id, avaliacao_id: uuid.UUID) -> Avaliacao:
    avaliacao = (await db.execute(
        select(Avaliacao).where(Avaliacao.id == avaliacao_id, Avaliacao.tenant_id == tenant_id)
    )).scalars().first()
    if not avaliacao:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada na sua instituição.")
    return avaliacao


async def _recalcular_nota_periodo(
    db: AsyncSession, tenant_id, usuario_id, matricula_id: uuid.UUID, disciplina_id: uuid.UUID, periodo_avaliacao: str
) -> None:
    """
    Recalcula (ou remove) a nota final do período de um aluno, como
    média ponderada das Avaliacao desse período que já têm nota
    lançada para ele — normalizada pelo peso total realmente presente,
    por isso continua correta mesmo com lançamentos parciais (ex.: só
    1 de 2 avaliações planeadas já avaliada) ou pesos que não somem
    exatamente 100. Não faz commit — quem chama decide quando (um
    lançamento em lote pode chamar isto várias vezes antes de committar).
    """
    linhas = (await db.execute(
        select(Avaliacao.peso, NotaAvaliacao.valor_nota)
        .join(NotaAvaliacao, NotaAvaliacao.avaliacao_id == Avaliacao.id)
        .where(
            Avaliacao.disciplina_id == disciplina_id,
            Avaliacao.periodo_avaliacao == periodo_avaliacao,
            NotaAvaliacao.matricula_id == matricula_id
        )
    )).all()

    existente = (await db.execute(
        select(RegistroNota).where(
            RegistroNota.matricula_id == matricula_id,
            RegistroNota.disciplina_id == disciplina_id,
            RegistroNota.periodo_avaliacao == periodo_avaliacao
        )
    )).scalars().first()

    peso_total = sum(Decimal(str(peso)) for peso, _ in linhas)
    if peso_total <= 0:
        # Já não há avaliações com nota para este aluno neste período.
        # Se a nota final aqui era calculada automaticamente, deixou de
        # ter base e é removida; uma nota digitada à mão antes desta
        # funcionalidade (calculada_automaticamente=False) nunca é tocada.
        if existente and existente.calculada_automaticamente:
            await db.delete(existente)
        return

    soma_ponderada = sum(Decimal(str(peso)) * Decimal(str(nota)) for peso, nota in linhas)
    valor_calculado = (soma_ponderada / peso_total).quantize(Decimal("0.01"))

    if existente:
        if existente.valor_nota != valor_calculado:
            # RN04 — regista a alteração mesmo quando a origem passa de
            # manual para calculada (é uma mudança real de valor).
            db.add(RegistroNotaAuditoria(
                tenant_id=tenant_id,
                registro_nota_id=existente.id,
                alterado_por=usuario_id,
                valor_antigo=existente.valor_nota,
                valor_novo=valor_calculado
            ))
            existente.valor_nota = valor_calculado
        existente.calculada_automaticamente = True
    else:
        db.add(RegistroNota(
            tenant_id=tenant_id,
            matricula_id=matricula_id,
            disciplina_id=disciplina_id,
            periodo_avaliacao=periodo_avaliacao,
            tipo_avaliacao=None,
            data_avaliacao=None,
            valor_nota=valor_calculado,
            calculada_automaticamente=True
        ))


async def listar_avaliacoes(
    db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, periodo_avaliacao: str | None = None
) -> list[Avaliacao]:
    """Lista as avaliações (provas/contínuas) de uma turma+disciplina, opcionalmente filtradas por período."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    query = select(Avaliacao).where(Avaliacao.turma_id == turma_id, Avaliacao.disciplina_id == disciplina_id)
    if periodo_avaliacao:
        query = query.where(Avaliacao.periodo_avaliacao == periodo_avaliacao)
    return (await db.execute(query.order_by(Avaliacao.data_criacao))).scalars().all()


async def listar_avaliacoes_agendadas(
    db: AsyncSession, utilizador: dict, data_inicio: date | None = None, data_fim: date | None = None
) -> list[dict]:
    """
    Avaliações/exames com agendamento (hora_inicio definida) num intervalo
    de datas — alimenta o painel do mapa de Horários. Gestor/Secretaria
    vê as de toda a escola; Professor só vê as das suas próprias
    alocações (RN01).
    """
    tenant_id = utilizador["tenant_id"]
    query = (
        select(Avaliacao, Turma.nome_codigo, Disciplina.nome)
        .join(Turma, Turma.id == Avaliacao.turma_id)
        .join(Disciplina, Disciplina.id == Avaliacao.disciplina_id)
        .where(Avaliacao.tenant_id == tenant_id, Avaliacao.hora_inicio.is_not(None))
    )
    if data_inicio:
        query = query.where(Avaliacao.data_avaliacao >= data_inicio)
    if data_fim:
        query = query.where(Avaliacao.data_avaliacao <= data_fim)

    perfil = utilizador["perfil_acesso"]
    if perfil == "PROFESSOR":
        professor = (await db.execute(
            select(Professor).where(
                Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == tenant_id
            )
        )).scalars().first()
        if not professor:
            return []
        pares = (await db.execute(
            select(ProfessorTurmaDisciplina.turma_id, ProfessorTurmaDisciplina.disciplina_id).where(
                ProfessorTurmaDisciplina.professor_id == professor.id, ProfessorTurmaDisciplina.tenant_id == tenant_id
            )
        )).all()
        if not pares:
            return []
        query = query.where(tuple_(Avaliacao.turma_id, Avaliacao.disciplina_id).in_(pares))
    elif perfil not in ("GESTOR", "SECRETARIA"):
        raise HTTPException(status_code=403, detail="Sem permissão para consultar avaliações agendadas.")

    query = query.order_by(Avaliacao.data_avaliacao, Avaliacao.hora_inicio)
    linhas = (await db.execute(query)).all()
    return [
        {
            "id": av.id,
            "titulo": av.titulo,
            "tipo_avaliacao": av.tipo_avaliacao,
            "periodo_avaliacao": av.periodo_avaliacao,
            "data_avaliacao": av.data_avaliacao,
            "hora_inicio": av.hora_inicio,
            "hora_fim": av.hora_fim,
            "sala": av.sala,
            "data_limite_correcao": av.data_limite_correcao,
            "grupo_agendamento_id": av.grupo_agendamento_id,
            "turma_id": av.turma_id,
            "turma_nome": turma_nome,
            "disciplina_id": av.disciplina_id,
            "disciplina_nome": disciplina_nome,
        }
        for av, turma_nome, disciplina_nome in linhas
    ]


async def criar_avaliacao(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, dados: AvaliacaoCreate) -> Avaliacao:
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, dados.periodo_avaliacao)
    tipo_config = await _validar_e_obter_tipo_avaliacao(db, tenant_id, dados.tipo_avaliacao)
    _validar_agendamento(tipo_config, utilizador, dados)
    if dados.peso <= 0:
        raise HTTPException(status_code=400, detail="O peso da avaliação tem de ser maior que zero.")
    await _validar_objetivo_aprendizagem(db, tenant_id, disciplina_id, dados.objetivo_aprendizagem_id)

    nova = Avaliacao(
        tenant_id=tenant_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        periodo_avaliacao=dados.periodo_avaliacao,
        titulo=dados.titulo.strip(),
        tipo_avaliacao=dados.tipo_avaliacao,
        peso=dados.peso,
        data_avaliacao=dados.data_avaliacao,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
        sala=dados.sala,
        data_limite_correcao=dados.data_limite_correcao,
        objetivo_aprendizagem_id=dados.objetivo_aprendizagem_id,
        criado_por_usuario_id=utilizador["usuario_id"]
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return nova


async def agendar_avaliacao_geral(db: AsyncSession, utilizador: dict, dados: "AvaliacaoAgendarGeralCreate") -> list[Avaliacao]:
    """
    Agendamento "Geral" (toda a escola) — só chamado por Gestor/Secretaria
    (RBAC no router). Cria uma Avaliacao por cada turma+disciplina
    atualmente alocada (ProfessorTurmaDisciplina), todas com a mesma
    data/hora/sala/prazo — cada professor lança a nota da sua
    normalmente, como já fazia antes.
    """
    tenant_id = utilizador["tenant_id"]
    await _validar_periodo_aberto(db, tenant_id, dados.periodo_avaliacao)
    await _validar_e_obter_tipo_avaliacao(db, tenant_id, dados.tipo_avaliacao)
    if dados.peso <= 0:
        raise HTTPException(status_code=400, detail="O peso da avaliação tem de ser maior que zero.")
    if dados.hora_fim <= dados.hora_inicio:
        raise HTTPException(status_code=400, detail="A hora de fim tem de ser depois da hora de início.")

    pares = (await db.execute(
        select(ProfessorTurmaDisciplina.turma_id, ProfessorTurmaDisciplina.disciplina_id)
        .where(ProfessorTurmaDisciplina.tenant_id == tenant_id)
        .distinct()
    )).all()
    if not pares:
        raise HTTPException(status_code=400, detail="Não há nenhuma turma com disciplinas alocadas — nada para agendar.")

    grupo_id = uuid.uuid4()
    titulo = dados.titulo.strip()
    novas = [
        Avaliacao(
            tenant_id=tenant_id,
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            periodo_avaliacao=dados.periodo_avaliacao,
            titulo=titulo,
            tipo_avaliacao=dados.tipo_avaliacao,
            peso=dados.peso,
            data_avaliacao=dados.data_avaliacao,
            hora_inicio=dados.hora_inicio,
            hora_fim=dados.hora_fim,
            sala=dados.sala,
            data_limite_correcao=dados.data_limite_correcao,
            grupo_agendamento_id=grupo_id,
            criado_por_usuario_id=utilizador["usuario_id"]
        )
        for turma_id, disciplina_id in pares
    ]
    db.add_all(novas)
    await db.commit()
    for nova in novas:
        await db.refresh(nova)
    return novas


async def atualizar_avaliacao(db: AsyncSession, utilizador: dict, avaliacao_id: uuid.UUID, dados: AvaliacaoUpdate) -> Avaliacao:
    tenant_id = utilizador["tenant_id"]
    avaliacao = await _obter_avaliacao(db, tenant_id, avaliacao_id)
    await _validar_autoria(db, utilizador, avaliacao.turma_id, avaliacao.disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, avaliacao.periodo_avaliacao)
    tipo_config = await _validar_e_obter_tipo_avaliacao(db, tenant_id, dados.tipo_avaliacao)
    _validar_agendamento(tipo_config, utilizador, dados)
    if dados.peso <= 0:
        raise HTTPException(status_code=400, detail="O peso da avaliação tem de ser maior que zero.")
    await _validar_objetivo_aprendizagem(db, tenant_id, avaliacao.disciplina_id, dados.objetivo_aprendizagem_id)

    peso_mudou = avaliacao.peso != dados.peso
    avaliacao.titulo = dados.titulo.strip()
    avaliacao.tipo_avaliacao = dados.tipo_avaliacao
    avaliacao.peso = dados.peso
    avaliacao.data_avaliacao = dados.data_avaliacao
    avaliacao.hora_inicio = dados.hora_inicio
    avaliacao.hora_fim = dados.hora_fim
    avaliacao.sala = dados.sala
    avaliacao.data_limite_correcao = dados.data_limite_correcao
    avaliacao.objetivo_aprendizagem_id = dados.objetivo_aprendizagem_id

    if peso_mudou:
        # O peso entra na fórmula da nota final — quem já tinha nota
        # nesta avaliação precisa de ver o período recalculado.
        matriculas_afetadas = (await db.execute(
            select(NotaAvaliacao.matricula_id).where(NotaAvaliacao.avaliacao_id == avaliacao_id)
        )).scalars().all()
        for matricula_id in matriculas_afetadas:
            await _recalcular_nota_periodo(db, tenant_id, utilizador["usuario_id"], matricula_id, avaliacao.disciplina_id, avaliacao.periodo_avaliacao)

    await db.commit()
    await db.refresh(avaliacao)
    return avaliacao


async def apagar_avaliacao(db: AsyncSession, utilizador: dict, avaliacao_id: uuid.UUID) -> None:
    tenant_id = utilizador["tenant_id"]
    avaliacao = await _obter_avaliacao(db, tenant_id, avaliacao_id)
    await _validar_autoria(db, utilizador, avaliacao.turma_id, avaliacao.disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, avaliacao.periodo_avaliacao)

    disciplina_id = avaliacao.disciplina_id
    periodo_avaliacao = avaliacao.periodo_avaliacao
    matriculas_afetadas = (await db.execute(
        select(NotaAvaliacao.matricula_id).where(NotaAvaliacao.avaliacao_id == avaliacao_id)
    )).scalars().all()

    await db.delete(avaliacao)  # cascade apaga as NotaAvaliacao associadas
    await db.flush()

    for matricula_id in matriculas_afetadas:
        await _recalcular_nota_periodo(db, tenant_id, utilizador["usuario_id"], matricula_id, disciplina_id, periodo_avaliacao)

    await db.commit()


async def listar_notas_avaliacao(db: AsyncSession, utilizador: dict, avaliacao_id: uuid.UUID) -> list[dict]:
    """Notas já lançadas numa avaliação — usado para pré-preencher o formulário ao reabri-la."""
    tenant_id = utilizador["tenant_id"]
    avaliacao = await _obter_avaliacao(db, tenant_id, avaliacao_id)
    await _validar_autoria(db, utilizador, avaliacao.turma_id, avaliacao.disciplina_id)

    resultado = await db.execute(
        select(NotaAvaliacao.matricula_id, NotaAvaliacao.valor_nota).where(NotaAvaliacao.avaliacao_id == avaliacao_id)
    )
    return [{"matricula_id": matricula_id, "valor_nota": float(valor)} for matricula_id, valor in resultado.all()]


async def lancar_notas_avaliacao_lote(db: AsyncSession, utilizador: dict, avaliacao_id: uuid.UUID, dados: NotaAvaliacaoLoteCreate) -> int:
    """
    Upsert das notas de uma avaliação concreta — dispara o recálculo da
    nota final do período (RegistroNota) para cada aluno afetado.
    RN02: valor_nota tem de estar entre 0.0 e 10.0.
    RN03: o período tem de estar aberto.
    RN05: passado o prazo de correção (data_limite_correcao), o
    Professor fica bloqueado — só Gestor/Secretaria pode lançar
    notas atrasadas.
    """
    tenant_id = utilizador["tenant_id"]
    avaliacao = await _obter_avaliacao(db, tenant_id, avaliacao_id)
    await _validar_autoria(db, utilizador, avaliacao.turma_id, avaliacao.disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, avaliacao.periodo_avaliacao)
    if (
        avaliacao.data_limite_correcao
        and avaliacao.data_limite_correcao < date.today()
        and utilizador["perfil_acesso"] not in ("GESTOR", "SECRETARIA")
    ):
        raise HTTPException(
            status_code=403,
            detail=f'Prazo de correção desta avaliação terminou em {avaliacao.data_limite_correcao.strftime("%d/%m/%Y")} — '
                   f"peça ao Gestor ou à Secretaria para lançar notas atrasadas."
        )

    matriculas_da_turma = set((await db.execute(
        select(Matricula.id).where(Matricula.turma_id == avaliacao.turma_id, Matricula.tenant_id == tenant_id)
    )).scalars().all())

    # Mesma razão das duas funções acima: uma query só para todas as
    # notas já existentes desta avaliação, em vez de um SELECT por
    # aluno dentro do loop.
    existentes_da_avaliacao = {
        r.matricula_id: r
        for r in (await db.execute(
            select(NotaAvaliacao).where(NotaAvaliacao.avaliacao_id == avaliacao_id)
        )).scalars().all()
    }

    total = 0
    matriculas_afetadas: set[uuid.UUID] = set()
    for item in dados.notas:
        if item.valor_nota < NOTA_MINIMA or item.valor_nota > NOTA_MAXIMA:
            raise HTTPException(
                status_code=400,
                detail=f"Nota {item.valor_nota} fora do intervalo permitido ({NOTA_MINIMA} a {NOTA_MAXIMA})."
            )
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = existentes_da_avaliacao.get(item.matricula_id)

        if existente:
            existente.valor_nota = item.valor_nota
        else:
            nova = NotaAvaliacao(
                tenant_id=tenant_id,
                avaliacao_id=avaliacao_id,
                matricula_id=item.matricula_id,
                valor_nota=item.valor_nota
            )
            db.add(nova)
            # Se o mesmo matricula_id aparecer duas vezes no mesmo lote
            # (não deveria, mas o formulário não impede), a segunda
            # ocorrência tem de encontrar esta — o dicionário só foi
            # construído uma vez, antes do loop.
            existentes_da_avaliacao[item.matricula_id] = nova
        matriculas_afetadas.add(item.matricula_id)
        total += 1

    await db.flush()

    for matricula_id in matriculas_afetadas:
        await _recalcular_nota_periodo(db, tenant_id, utilizador["usuario_id"], matricula_id, avaliacao.disciplina_id, avaliacao.periodo_avaliacao)

    await db.commit()
    return total


async def listar_notas_finais(
    db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, periodo_avaliacao: str
) -> list[dict]:
    """
    Nota final de cada aluno da turma para um período — calculada
    (a partir das avaliações) ou manual (lançada diretamente, de antes
    desta funcionalidade existir), lado a lado com quem ainda não tem
    nenhuma.
    """
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    resultado = await db.execute(
        select(Matricula.id, Aluno.nome_completo, RegistroNota.valor_nota, RegistroNota.calculada_automaticamente)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .outerjoin(RegistroNota, (RegistroNota.matricula_id == Matricula.id)
                   & (RegistroNota.disciplina_id == disciplina_id)
                   & (RegistroNota.periodo_avaliacao == periodo_avaliacao))
        .where(Matricula.turma_id == turma_id, Matricula.status_matricula == "ATIVO", Matricula.tenant_id == tenant_id)
        .order_by(Aluno.nome_completo)
    )
    return [
        {
            "matricula_id": matricula_id,
            "nome_aluno": nome_aluno,
            "valor_nota": float(valor_nota) if valor_nota is not None else None,
            "calculada_automaticamente": bool(calculada) if calculada is not None else False,
        }
        for matricula_id, nome_aluno, valor_nota, calculada in resultado.all()
    ]
