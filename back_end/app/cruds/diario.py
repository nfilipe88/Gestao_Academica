"""Acesso a dados e regras de negócio (RN01-RN04) do Diário de Classe."""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import date
from decimal import Decimal
import uuid

from app.database.models_academico import Disciplina, Turma
from app.database.models_pessoas import Aluno, Professor
from app.database.models_matricula import Matricula
from app.database.models_diario import (
    Avaliacao, NotaAvaliacao, PeriodoAvaliacao, ProfessorTurmaDisciplina,
    RegistroFrequencia, RegistroNota, RegistroNotaAuditoria
)
from app.schemas.diario import (
    AvaliacaoCreate, AvaliacaoUpdate, FrequenciaLoteCreate, NotaAvaliacaoLoteCreate, NotaLoteCreate, PeriodoAvaliacaoCreate
)

NOTA_MINIMA = Decimal("0.0")
NOTA_MAXIMA = Decimal("10.0")
TIPOS_AVALIACAO_VALIDOS = {"CONTINUA", "PROVA"}


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

    total = 0
    for item in dados.frequencias:
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = (await db.execute(
            select(RegistroFrequencia).where(
                RegistroFrequencia.matricula_id == item.matricula_id,
                RegistroFrequencia.disciplina_id == disciplina_id,
                RegistroFrequencia.data_aula == dados.data_aula
            )
        )).scalars().first()

        if existente:
            # Upsert: relançar a chamada do mesmo dia atualiza, não duplica.
            existente.presenca = item.presenca
            existente.faltas = item.faltas
            existente.quantidade_aulas = dados.quantidade_aulas
            existente.conteudo_programado = dados.conteudo_programado
        else:
            db.add(RegistroFrequencia(
                tenant_id=tenant_id,
                matricula_id=item.matricula_id,
                disciplina_id=disciplina_id,
                data_aula=dados.data_aula,
                quantidade_aulas=dados.quantidade_aulas,
                conteudo_programado=dados.conteudo_programado,
                presenca=item.presenca,
                faltas=item.faltas
            ))
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

    total = 0
    for item in dados.notas:
        if item.valor_nota < NOTA_MINIMA or item.valor_nota > NOTA_MAXIMA:
            raise HTTPException(
                status_code=400,
                detail=f"Nota {item.valor_nota} fora do intervalo permitido ({NOTA_MINIMA} a {NOTA_MAXIMA})."
            )
        if item.matricula_id not in matriculas_da_turma:
            raise HTTPException(status_code=400, detail=f"A matrícula {item.matricula_id} não pertence a esta turma.")

        existente = (await db.execute(
            select(RegistroNota).where(
                RegistroNota.matricula_id == item.matricula_id,
                RegistroNota.disciplina_id == disciplina_id,
                RegistroNota.periodo_avaliacao == dados.periodo_avaliacao
            )
        )).scalars().first()

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
            db.add(RegistroNota(
                tenant_id=tenant_id,
                matricula_id=item.matricula_id,
                disciplina_id=disciplina_id,
                periodo_avaliacao=dados.periodo_avaliacao,
                tipo_avaliacao=dados.tipo_avaliacao,
                data_avaliacao=dados.data_avaliacao,
                valor_nota=item.valor_nota
            ))
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
def _validar_tipo_avaliacao(tipo: str):
    if tipo not in TIPOS_AVALIACAO_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f'Tipo de avaliação inválido — use {" ou ".join(sorted(TIPOS_AVALIACAO_VALIDOS))}.'
        )


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


async def criar_avaliacao(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID, dados: AvaliacaoCreate) -> Avaliacao:
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, dados.periodo_avaliacao)
    _validar_tipo_avaliacao(dados.tipo_avaliacao)
    if dados.peso <= 0:
        raise HTTPException(status_code=400, detail="O peso da avaliação tem de ser maior que zero.")

    nova = Avaliacao(
        tenant_id=tenant_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        periodo_avaliacao=dados.periodo_avaliacao,
        titulo=dados.titulo.strip(),
        tipo_avaliacao=dados.tipo_avaliacao,
        peso=dados.peso,
        data_avaliacao=dados.data_avaliacao,
        criado_por_usuario_id=utilizador["usuario_id"]
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return nova


async def atualizar_avaliacao(db: AsyncSession, utilizador: dict, avaliacao_id: uuid.UUID, dados: AvaliacaoUpdate) -> Avaliacao:
    tenant_id = utilizador["tenant_id"]
    avaliacao = await _obter_avaliacao(db, tenant_id, avaliacao_id)
    await _validar_autoria(db, utilizador, avaliacao.turma_id, avaliacao.disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, avaliacao.periodo_avaliacao)
    _validar_tipo_avaliacao(dados.tipo_avaliacao)
    if dados.peso <= 0:
        raise HTTPException(status_code=400, detail="O peso da avaliação tem de ser maior que zero.")

    peso_mudou = avaliacao.peso != dados.peso
    avaliacao.titulo = dados.titulo.strip()
    avaliacao.tipo_avaliacao = dados.tipo_avaliacao
    avaliacao.peso = dados.peso
    avaliacao.data_avaliacao = dados.data_avaliacao

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
    """
    tenant_id = utilizador["tenant_id"]
    avaliacao = await _obter_avaliacao(db, tenant_id, avaliacao_id)
    await _validar_autoria(db, utilizador, avaliacao.turma_id, avaliacao.disciplina_id)
    await _validar_periodo_aberto(db, tenant_id, avaliacao.periodo_avaliacao)

    matriculas_da_turma = set((await db.execute(
        select(Matricula.id).where(Matricula.turma_id == avaliacao.turma_id, Matricula.tenant_id == tenant_id)
    )).scalars().all())

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

        existente = (await db.execute(
            select(NotaAvaliacao).where(
                NotaAvaliacao.avaliacao_id == avaliacao_id,
                NotaAvaliacao.matricula_id == item.matricula_id
            )
        )).scalars().first()

        if existente:
            existente.valor_nota = item.valor_nota
        else:
            db.add(NotaAvaliacao(
                tenant_id=tenant_id,
                avaliacao_id=avaliacao_id,
                matricula_id=item.matricula_id,
                valor_nota=item.valor_nota
            ))
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
