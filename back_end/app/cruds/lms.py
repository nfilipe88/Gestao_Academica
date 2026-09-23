"""
LMS mínimo: gestão de materiais de aula pelo professor/staff.

A leitura do lado do aluno (Portal) vive em cruds/portal.py — este
módulo só trata da autoria (quem pode publicar/editar/apagar um
material), seguindo a mesma RN01 já usada em cruds/diario.py e
cruds/tarefas.py: Gestor/Secretaria em qualquer turma, Professor só
nas turmas+disciplinas onde está alocado.
"""
import random
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.models import Tenant
from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, Professor
from app.database.models_diario import Avaliacao, PeriodoAvaliacao, ProfessorTurmaDisciplina
from app.database.models_lms import LMSExame, LMSExameQuestao, LMSGrupoExameAtribuicao, LMSQuestao, LMSTentativaExame, MaterialAula
from app.core import prof_virtual
from app.cruds import diario as crud_diario
from app.cruds import notificacoes as crud_notificacoes
from app.schemas.diario import AvaliacaoCreate
from app.schemas.lms import (
    LMSCorrigirTentativaInput, LMSGrupoExameCreate, LMSQuestaoCreate, LMSQuestaoUpdate, LMSReatribuirVarianteInput,
    LMSSubmeterTentativa, MaterialAulaCreate, MaterialAulaUpdate, SugestaoConteudoCreate
)


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
    """RN01 (mesma regra do Diário de Classe): Gestor/Secretaria têm acesso a qualquer turma; Professor só às suas."""
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return

    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para gerir materiais de aula.")

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


async def _validar_objetivo_aprendizagem(db: AsyncSession, tenant_id, disciplina_id: uuid.UUID, objetivo_id: uuid.UUID | None):
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


async def _obter_material(db: AsyncSession, tenant_id, material_id: uuid.UUID) -> MaterialAula:
    material = (await db.execute(
        select(MaterialAula).where(MaterialAula.id == material_id, MaterialAula.tenant_id == tenant_id)
    )).scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Material de aula não encontrado na sua instituição.")
    return material


async def listar_materiais(db: AsyncSession, utilizador: dict, turma_id: uuid.UUID, disciplina_id: uuid.UUID) -> list[MaterialAula]:
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, turma_id, disciplina_id)
    await _validar_autoria(db, utilizador, turma_id, disciplina_id)

    return (await db.execute(
        select(MaterialAula)
        .where(MaterialAula.turma_id == turma_id, MaterialAula.disciplina_id == disciplina_id)
        .order_by(MaterialAula.data_criacao.desc())
    )).scalars().all()


async def criar_material(db: AsyncSession, utilizador: dict, dados: MaterialAulaCreate) -> MaterialAula:
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, dados.turma_id, dados.disciplina_id)
    await _validar_autoria(db, utilizador, dados.turma_id, dados.disciplina_id)
    await _validar_objetivo_aprendizagem(db, tenant_id, dados.disciplina_id, dados.objetivo_aprendizagem_id)

    novo = MaterialAula(
        tenant_id=tenant_id,
        turma_id=dados.turma_id,
        disciplina_id=dados.disciplina_id,
        titulo=dados.titulo.strip(),
        corpo=dados.corpo,
        objetivo_aprendizagem_id=dados.objetivo_aprendizagem_id,
        publicado=dados.publicado,
        criado_por_usuario_id=utilizador["usuario_id"]
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return novo


async def atualizar_material(db: AsyncSession, utilizador: dict, material_id: uuid.UUID, dados: MaterialAulaUpdate) -> MaterialAula:
    tenant_id = utilizador["tenant_id"]
    material = await _obter_material(db, tenant_id, material_id)
    await _validar_autoria(db, utilizador, material.turma_id, material.disciplina_id)
    await _validar_objetivo_aprendizagem(db, tenant_id, material.disciplina_id, dados.objetivo_aprendizagem_id)

    material.titulo = dados.titulo.strip()
    material.corpo = dados.corpo
    material.objetivo_aprendizagem_id = dados.objetivo_aprendizagem_id
    material.publicado = dados.publicado
    await db.commit()
    await db.refresh(material)
    return material


async def apagar_material(db: AsyncSession, utilizador: dict, material_id: uuid.UUID) -> None:
    tenant_id = utilizador["tenant_id"]
    material = await _obter_material(db, tenant_id, material_id)
    await _validar_autoria(db, utilizador, material.turma_id, material.disciplina_id)

    await db.delete(material)
    await db.commit()


async def sugerir_conteudo(db: AsyncSession, utilizador: dict, dados: SugestaoConteudoCreate) -> str:
    """Pede ao Prof. Virtual um rascunho do campo Conteúdo, a partir do título — o professor revê antes de publicar."""
    tenant_id = utilizador["tenant_id"]
    await _validar_turma_disciplina(db, tenant_id, dados.turma_id, dados.disciplina_id)
    await _validar_autoria(db, utilizador, dados.turma_id, dados.disciplina_id)
    await _validar_objetivo_aprendizagem(db, tenant_id, dados.disciplina_id, dados.objetivo_aprendizagem_id)

    turma = (await db.execute(
        select(Turma).where(Turma.id == dados.turma_id, Turma.tenant_id == tenant_id)
    )).scalars().first()
    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == dados.disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()

    nome_objetivo = None
    if dados.objetivo_aprendizagem_id:
        objetivo = (await db.execute(
            select(ObjetivoAprendizagem).where(ObjetivoAprendizagem.id == dados.objetivo_aprendizagem_id)
        )).scalars().first()
        nome_objetivo = objetivo.nome if objetivo else None

    return await prof_virtual.sugerir_conteudo_aula(
        titulo=dados.titulo.strip(),
        nome_disciplina=disciplina.nome,
        nome_turma=turma.nome_codigo,
        nome_objetivo=nome_objetivo,
        instrucoes=dados.instrucoes.strip() if dados.instrucoes else None
    )


# ==========================================
# BANCO DE QUESTÕES
# ==========================================
async def _validar_autoria_disciplina(db: AsyncSession, utilizador: dict, disciplina_id: uuid.UUID):
    """RN01 (mesma regra do resto do LMS): Gestor/Secretaria têm acesso a qualquer disciplina; Professor só às que lecciona nalguma turma."""
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return
    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para gerir o banco de questões.")

    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=403, detail="Utilizador não corresponde a nenhum professor cadastrado.")

    alocado = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.professor_id == professor.id,
            ProfessorTurmaDisciplina.disciplina_id == disciplina_id
        )
    )).scalars().first()
    if not alocado:
        raise HTTPException(status_code=403, detail="Não lecciona esta disciplina.")


async def _obter_questao(db: AsyncSession, tenant_id, questao_id: uuid.UUID) -> LMSQuestao:
    questao = (await db.execute(
        select(LMSQuestao).where(LMSQuestao.id == questao_id, LMSQuestao.tenant_id == tenant_id)
    )).scalars().first()
    if not questao:
        raise HTTPException(status_code=404, detail="Questão não encontrada na sua instituição.")
    return questao


async def listar_banco_questoes(db: AsyncSession, utilizador: dict, disciplina_id: uuid.UUID) -> list[LMSQuestao]:
    tenant_id = utilizador["tenant_id"]
    await _validar_autoria_disciplina(db, utilizador, disciplina_id)
    return (await db.execute(
        select(LMSQuestao)
        .where(LMSQuestao.disciplina_id == disciplina_id, LMSQuestao.tenant_id == tenant_id)
        .order_by(LMSQuestao.data_criacao.desc())
    )).scalars().all()


async def criar_questao(db: AsyncSession, utilizador: dict, dados: LMSQuestaoCreate) -> LMSQuestao:
    tenant_id = utilizador["tenant_id"]
    await _validar_autoria_disciplina(db, utilizador, dados.disciplina_id)

    nova = LMSQuestao(
        tenant_id=tenant_id,
        disciplina_id=dados.disciplina_id,
        enunciado=dados.enunciado.strip(),
        tipo=dados.tipo,
        opcoes=dados.opcoes,
        resposta_correta=dados.resposta_correta,
        valor=dados.valor,
        criado_por_usuario_id=utilizador["usuario_id"]
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return nova


async def atualizar_questao(db: AsyncSession, utilizador: dict, questao_id: uuid.UUID, dados: LMSQuestaoUpdate) -> LMSQuestao:
    tenant_id = utilizador["tenant_id"]
    questao = await _obter_questao(db, tenant_id, questao_id)
    await _validar_autoria_disciplina(db, utilizador, questao.disciplina_id)

    questao.enunciado = dados.enunciado.strip()
    questao.tipo = dados.tipo
    questao.opcoes = dados.opcoes
    questao.resposta_correta = dados.resposta_correta
    questao.valor = dados.valor
    await db.commit()
    await db.refresh(questao)
    return questao


async def apagar_questao(db: AsyncSession, utilizador: dict, questao_id: uuid.UUID) -> None:
    tenant_id = utilizador["tenant_id"]
    questao = await _obter_questao(db, tenant_id, questao_id)
    await _validar_autoria_disciplina(db, utilizador, questao.disciplina_id)

    ja_usada = (await db.execute(
        select(LMSExameQuestao).where(LMSExameQuestao.questao_id == questao_id)
    )).scalars().first()
    if ja_usada:
        raise HTTPException(status_code=400, detail="Esta questão já foi usada num exame — não pode ser apagada (pode deixar de a usar em exames futuros).")

    await db.delete(questao)
    await db.commit()


# ==========================================
# EXAMES (motor online) — gestão pelo professor/staff
# ==========================================
async def _obter_alocacao(db: AsyncSession, tenant_id, alocacao_id: uuid.UUID) -> ProfessorTurmaDisciplina:
    alocacao = (await db.execute(
        select(ProfessorTurmaDisciplina).where(
            ProfessorTurmaDisciplina.id == alocacao_id, ProfessorTurmaDisciplina.tenant_id == tenant_id
        )
    )).scalars().first()
    if not alocacao:
        raise HTTPException(status_code=404, detail="Alocação (Professor/Turma/Disciplina) não encontrada na sua instituição.")
    return alocacao


async def _validar_autoria_alocacao(db: AsyncSession, utilizador: dict, alocacao: ProfessorTurmaDisciplina):
    """RN01 (mesma regra do resto do LMS/Trabalhos): Gestor/Secretaria têm acesso a qualquer turma; Professor só à sua própria alocação."""
    perfil = utilizador["perfil_acesso"]
    if perfil in ("GESTOR", "SECRETARIA"):
        return
    if perfil != "PROFESSOR":
        raise HTTPException(status_code=403, detail="Sem permissão para gerir exames.")

    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"], Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor or professor.id != alocacao.professor_id:
        raise HTTPException(status_code=403, detail="Não lecciona esta disciplina nesta turma.")


async def _obter_exame(db: AsyncSession, tenant_id, exame_id: uuid.UUID) -> LMSExame:
    exame = (await db.execute(
        select(LMSExame).where(LMSExame.id == exame_id, LMSExame.tenant_id == tenant_id)
    )).scalars().first()
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado na sua instituição.")
    return exame


async def listar_grupos_exame(db: AsyncSession, utilizador: dict, alocacao_id: uuid.UUID) -> list[dict]:
    """Agrupa as variantes por grupo_id para a listagem do professor/staff — cada grupo aparece uma só vez."""
    tenant_id = utilizador["tenant_id"]
    alocacao = await _obter_alocacao(db, tenant_id, alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    exames = (await db.execute(
        select(LMSExame)
        .where(LMSExame.alocacao_id == alocacao_id, LMSExame.tenant_id == tenant_id)
        .order_by(LMSExame.data_inicio.desc(), LMSExame.letra_variante)
    )).scalars().all()

    grupos: dict[uuid.UUID, list[LMSExame]] = {}
    for exame in exames:
        grupos.setdefault(exame.grupo_id, []).append(exame)

    return [
        {
            "grupo_id": grupo_id,
            "titulo": variantes[0].titulo,
            "data_inicio": variantes[0].data_inicio,
            "data_fim": variantes[0].data_fim,
            "duracao_minutos": variantes[0].duracao_minutos,
            "modalidade": variantes[0].modalidade,
            "publicado": variantes[0].publicado,
            "iniciado": variantes[0].iniciado,
            "iniciado_em": variantes[0].iniciado_em,
            "avaliacao_id": variantes[0].avaliacao_id,
            "variantes": [{"exame_id": v.id, "letra_variante": v.letra_variante} for v in variantes],
        }
        # dict em Python 3.7+ preserva a ordem de inserção — como `exames`
        # já veio ordenado por data_inicio desc, os grupos saem na mesma ordem.
        for grupo_id, variantes in grupos.items()
    ]


async def criar_grupo_exame(db: AsyncSession, utilizador: dict, dados: LMSGrupoExameCreate) -> list[LMSExame]:
    """Cria a Avaliacao que vai receber as notas (reaproveita por
    inteiro cruds/diario.py::criar_avaliacao — RN01/RN03/tipo ativo/
    peso já validados lá) e, de seguida, uma LMSExame por variante,
    todas a partilhar o mesmo grupo_id/avaliacao_id. Ainda draft
    (publicado=False, iniciado=False) — só cruds/lms.py::iniciar_grupo_exame
    abre aos alunos."""
    tenant_id = utilizador["tenant_id"]
    alocacao = await _obter_alocacao(db, tenant_id, dados.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    avaliacao = await crud_diario.criar_avaliacao(
        db, utilizador, alocacao.turma_id, alocacao.disciplina_id,
        AvaliacaoCreate(
            periodo_avaliacao=dados.periodo_avaliacao, titulo=dados.titulo.strip(),
            tipo_avaliacao=dados.tipo_avaliacao, peso=dados.peso
        )
    )

    grupo_id = uuid.uuid4()
    exames_criados: list[LMSExame] = []
    for indice, variante in enumerate(dados.variantes):
        letra = variante.letra_variante or chr(ord("A") + indice)
        questoes = (await db.execute(
            select(LMSQuestao).where(LMSQuestao.id.in_(variante.questao_ids), LMSQuestao.tenant_id == tenant_id)
        )).scalars().all()
        if len(questoes) != len(variante.questao_ids):
            raise HTTPException(status_code=404, detail=f'Uma ou mais questões da variante "{letra}" não foram encontradas na sua instituição.')
        if any(q.disciplina_id != alocacao.disciplina_id for q in questoes):
            raise HTTPException(status_code=400, detail=f'Todas as questões da variante "{letra}" têm de ser da disciplina desta alocação.')

        novo_exame = LMSExame(
            tenant_id=tenant_id,
            alocacao_id=dados.alocacao_id,
            titulo=dados.titulo.strip(),
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
            duracao_minutos=dados.duracao_minutos,
            baralhar_perguntas=dados.baralhar_perguntas,
            publicado=False,
            grupo_id=grupo_id,
            letra_variante=letra,
            modalidade=dados.modalidade,
            avaliacao_id=avaliacao.id,
            criado_por_usuario_id=utilizador["usuario_id"]
        )
        db.add(novo_exame)
        await db.flush()  # obter o id do exame sem ainda fechar a transação

        for ordem, questao_id in enumerate(variante.questao_ids):
            db.add(LMSExameQuestao(tenant_id=tenant_id, exame_id=novo_exame.id, questao_id=questao_id, ordem=ordem))
        exames_criados.append(novo_exame)

    await db.commit()
    for exame in exames_criados:
        await db.refresh(exame)
    return exames_criados


async def iniciar_grupo_exame(db: AsyncSession, utilizador: dict, grupo_id: uuid.UUID) -> list[LMSExame]:
    """Gatilho exclusivo de Gestor/Secretaria (ver _PODE_INICIAR_EXAME
    em api/v1/lms.py) — abre o grupo inteiro aos alunos (publicado E
    iniciado passam a True em todas as variantes) e distribui cada
    aluno com matrícula ATIVO na turma por round-robin entre as
    variantes, gravado uma única vez em LMSGrupoExameAtribuicao."""
    tenant_id = utilizador["tenant_id"]
    exames = (await db.execute(
        select(LMSExame).where(LMSExame.grupo_id == grupo_id, LMSExame.tenant_id == tenant_id)
        .order_by(LMSExame.letra_variante)
    )).scalars().all()
    if not exames:
        raise HTTPException(status_code=404, detail="Grupo de exame não encontrado na sua instituição.")
    if exames[0].iniciado:
        raise HTTPException(status_code=400, detail="Este grupo já foi iniciado.")

    alocacao = await _obter_alocacao(db, tenant_id, exames[0].alocacao_id)
    if exames[0].avaliacao_id:
        # Defesa extra: o período já foi validado na criação da
        # Avaliacao (ver criar_grupo_exame), mas pode ter sido
        # trancado pela secretaria entretanto — não deixa iniciar
        # um grupo cujo período já fechou.
        avaliacao = (await db.execute(
            select(Avaliacao).where(Avaliacao.id == exames[0].avaliacao_id, Avaliacao.tenant_id == tenant_id)
        )).scalars().first()
        if avaliacao:
            periodo = (await db.execute(
                select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id, PeriodoAvaliacao.nome == avaliacao.periodo_avaliacao)
            )).scalars().first()
            if periodo and not periodo.aberto:
                raise HTTPException(
                    status_code=403,
                    detail=f'O período de avaliação "{avaliacao.periodo_avaliacao}" foi trancado pela secretaria — já não é possível iniciar este grupo.'
                )

    matriculas = (await db.execute(
        select(Matricula.id).where(
            Matricula.turma_id == alocacao.turma_id, Matricula.tenant_id == tenant_id,
            Matricula.status_matricula == "ATIVO"
        ).order_by(Matricula.id)  # ordem estável — nunca a ordem "de sorte" de inserção
    )).scalars().all()

    agora = datetime.now(timezone.utc)
    for indice, matricula_id in enumerate(matriculas):
        exame_atribuido = exames[indice % len(exames)]
        db.add(LMSGrupoExameAtribuicao(
            tenant_id=tenant_id, grupo_id=grupo_id, matricula_id=matricula_id, exame_id=exame_atribuido.id,
            atribuido_manualmente=False, atribuido_por_usuario_id=utilizador["usuario_id"]
        ))

    for exame in exames:
        exame.publicado = True
        exame.iniciado = True
        exame.iniciado_em = agora
        exame.iniciado_por_usuario_id = utilizador["usuario_id"]

    await db.commit()
    for exame in exames:
        await db.refresh(exame)
    return exames


async def reatribuir_variante_aluno(db: AsyncSession, utilizador: dict, grupo_id: uuid.UUID, dados: LMSReatribuirVarianteInput) -> LMSGrupoExameAtribuicao:
    """Mesma RBAC de iniciar_grupo_exame — reatribuição manual pelo
    Gestor. Bloqueada se o aluno já tiver começado a variante atual
    (nunca órfão uma tentativa em curso)."""
    tenant_id = utilizador["tenant_id"]
    atribuicao = (await db.execute(
        select(LMSGrupoExameAtribuicao).where(
            LMSGrupoExameAtribuicao.grupo_id == grupo_id, LMSGrupoExameAtribuicao.matricula_id == dados.matricula_id,
            LMSGrupoExameAtribuicao.tenant_id == tenant_id
        )
    )).scalars().first()
    if not atribuicao:
        raise HTTPException(status_code=404, detail="Este aluno ainda não foi atribuído a nenhuma variante deste grupo (o grupo já foi iniciado?).")

    destino = (await db.execute(
        select(LMSExame).where(LMSExame.id == dados.exame_id, LMSExame.grupo_id == grupo_id, LMSExame.tenant_id == tenant_id)
    )).scalars().first()
    if not destino:
        raise HTTPException(status_code=400, detail="A variante de destino não pertence a este grupo.")

    ja_tem_tentativa = (await db.execute(
        select(LMSTentativaExame).where(
            LMSTentativaExame.exame_id == atribuicao.exame_id, LMSTentativaExame.matricula_id == dados.matricula_id
        )
    )).scalars().first()
    if ja_tem_tentativa:
        raise HTTPException(status_code=400, detail="Este aluno já iniciou a tentativa na variante atual — não pode ser reatribuído.")

    atribuicao.exame_id = dados.exame_id
    atribuicao.atribuido_manualmente = True
    atribuicao.atribuido_por_usuario_id = utilizador["usuario_id"]
    await db.commit()
    await db.refresh(atribuicao)
    return atribuicao


async def listar_atribuicoes_grupo(db: AsyncSession, utilizador: dict, grupo_id: uuid.UUID) -> list[dict]:
    """Quem está atribuído a cada variante — alimenta a tabela de
    reatribuição manual do Gestor (ver reatribuir_variante_aluno).
    Vazio antes do INICIAR (a distribuição só existe a partir daí)."""
    tenant_id = utilizador["tenant_id"]
    exames = (await db.execute(
        select(LMSExame).where(LMSExame.grupo_id == grupo_id, LMSExame.tenant_id == tenant_id)
    )).scalars().all()
    if not exames:
        raise HTTPException(status_code=404, detail="Grupo de exame não encontrado na sua instituição.")
    alocacao = await _obter_alocacao(db, tenant_id, exames[0].alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    letra_por_exame = {e.id: e.letra_variante for e in exames}
    linhas = (await db.execute(
        select(LMSGrupoExameAtribuicao, Aluno.nome_completo)
        .join(Matricula, Matricula.id == LMSGrupoExameAtribuicao.matricula_id)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(LMSGrupoExameAtribuicao.grupo_id == grupo_id, LMSGrupoExameAtribuicao.tenant_id == tenant_id)
        .order_by(Aluno.nome_completo)
    )).all()

    return [
        {
            "matricula_id": atribuicao.matricula_id,
            "nome_aluno": nome_aluno,
            "exame_id": atribuicao.exame_id,
            "letra_variante": letra_por_exame.get(atribuicao.exame_id),
            "atribuido_manualmente": atribuicao.atribuido_manualmente,
        }
        for atribuicao, nome_aluno in linhas
    ]


async def alternar_publicacao_exame(db: AsyncSession, utilizador: dict, exame_id: uuid.UUID, publicado: bool) -> LMSExame:
    tenant_id = utilizador["tenant_id"]
    exame = await _obter_exame(db, tenant_id, exame_id)
    alocacao = await _obter_alocacao(db, tenant_id, exame.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    exame.publicado = publicado
    await db.commit()
    await db.refresh(exame)
    return exame


async def apagar_grupo_exame(db: AsyncSession, utilizador: dict, grupo_id: uuid.UUID) -> None:
    """Apaga TODAS as variantes do grupo de uma vez — nunca deixa uma
    variante órfã (sem irmãs) presa a uma Avaliacao partilhada ou a
    atribuições que já não fazem sentido."""
    tenant_id = utilizador["tenant_id"]
    exames = (await db.execute(
        select(LMSExame).where(LMSExame.grupo_id == grupo_id, LMSExame.tenant_id == tenant_id)
    )).scalars().all()
    if not exames:
        raise HTTPException(status_code=404, detail="Grupo de exame não encontrado na sua instituição.")

    alocacao = await _obter_alocacao(db, tenant_id, exames[0].alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    exame_ids = [e.id for e in exames]
    ja_tem_tentativa = (await db.execute(
        select(LMSTentativaExame.id).where(LMSTentativaExame.exame_id.in_(exame_ids)).limit(1)
    )).scalars().first()
    if ja_tem_tentativa:
        raise HTTPException(status_code=400, detail="Este grupo já tem tentativas de alunos — não pode ser apagado (pode despublicá-lo).")

    for exame in exames:
        await db.delete(exame)  # cascade apaga LMSExameQuestao e LMSGrupoExameAtribuicao (via exame_id)
    await db.commit()


async def obter_exame_com_gabarito(db: AsyncSession, utilizador: dict, exame_id: uuid.UUID) -> dict:
    """Detalhe do exame para o professor rever — inclui a resposta certa de cada questão, nunca exposto ao aluno (ver obter_perguntas_tentativa)."""
    tenant_id = utilizador["tenant_id"]
    exame = await _obter_exame(db, tenant_id, exame_id)
    alocacao = await _obter_alocacao(db, tenant_id, exame.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    linhas = (await db.execute(
        select(LMSExameQuestao, LMSQuestao)
        .join(LMSQuestao, LMSQuestao.id == LMSExameQuestao.questao_id)
        .where(LMSExameQuestao.exame_id == exame_id)
        .order_by(LMSExameQuestao.ordem)
    )).all()

    return {
        "id": exame.id,
        "titulo": exame.titulo,
        "data_inicio": exame.data_inicio,
        "data_fim": exame.data_fim,
        "duracao_minutos": exame.duracao_minutos,
        "baralhar_perguntas": exame.baralhar_perguntas,
        "publicado": exame.publicado,
        "grupo_id": exame.grupo_id,
        "letra_variante": exame.letra_variante,
        "modalidade": exame.modalidade,
        "iniciado": exame.iniciado,
        "perguntas": [
            {
                "id": questao.id, "enunciado": questao.enunciado, "tipo": questao.tipo,
                "opcoes": questao.opcoes, "resposta_correta": questao.resposta_correta, "valor": questao.valor,
            }
            for _, questao in linhas
        ],
    }


def _derivar_status_tentativa(tentativa: LMSTentativaExame) -> str:
    """EM_CURSO/NAO_INICIADA continuam derivados de data_submissao;
    SUBMETIDA passa a ter dois casos possíveis por trás (sempre 100%
    automática, ou finalizada manualmente) — distinguidos por
    corrigida_finalizada, que introduz o terceiro estado AGUARDA_CORRECAO
    (submetida, mas com pelo menos uma questão ABERTA por pontuar)."""
    if not tentativa.data_submissao:
        return "EM_CURSO"
    return "SUBMETIDA" if tentativa.corrigida_finalizada else "AGUARDA_CORRECAO"


async def listar_resultados_exame(db: AsyncSession, utilizador: dict, exame_id: uuid.UUID) -> list[dict]:
    """Notas de quem já começou/submeteu este exame — para o professor corrigir/exportar. Quem ainda não começou não aparece aqui."""
    tenant_id = utilizador["tenant_id"]
    exame = await _obter_exame(db, tenant_id, exame_id)
    alocacao = await _obter_alocacao(db, tenant_id, exame.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    linhas = (await db.execute(
        select(LMSTentativaExame, Aluno.nome_completo)
        .join(Matricula, Matricula.id == LMSTentativaExame.matricula_id)
        .join(Aluno, Aluno.id == Matricula.aluno_id)
        .where(LMSTentativaExame.exame_id == exame_id)
        .order_by(Aluno.nome_completo)
    )).all()

    return [
        {
            "matricula_id": tentativa.matricula_id,
            "nome_aluno": nome_aluno,
            "exame_id": tentativa.exame_id,
            "status": _derivar_status_tentativa(tentativa),
            "nota_obtida": tentativa.nota_obtida,
            "nota_maxima": tentativa.nota_maxima,
            "eventos_suspeitos": tentativa.eventos_suspeitos,
            "data_inicio": tentativa.data_inicio,
            "data_submissao": tentativa.data_submissao,
            "corrigida_finalizada": tentativa.corrigida_finalizada,
            "correcoes_manuais": tentativa.correcoes_manuais,
            "corrigido_por_usuario_id": tentativa.corrigido_por_usuario_id,
            "corrigido_em": tentativa.corrigido_em,
            # Respostas em bruto — precisa o staff para corrigir as
            # questões ABERTA (ver corrigir_tentativa); as objetivas já
            # se veem no gabarito (obter_exame_com_gabarito).
            "respostas": tentativa.respostas,
        }
        for tentativa, nome_aluno in linhas
    ]


async def listar_resultados_grupo(db: AsyncSession, utilizador: dict, grupo_id: uuid.UUID) -> list[dict]:
    """Conveniência: agrega os resultados de todas as variantes do
    grupo numa só lista (com letra_variante em cada linha), para o
    staff não ter de abrir resultado a resultado por variante."""
    tenant_id = utilizador["tenant_id"]
    exames = (await db.execute(
        select(LMSExame).where(LMSExame.grupo_id == grupo_id, LMSExame.tenant_id == tenant_id)
        .order_by(LMSExame.letra_variante)
    )).scalars().all()
    if not exames:
        raise HTTPException(status_code=404, detail="Grupo de exame não encontrado na sua instituição.")

    alocacao = await _obter_alocacao(db, tenant_id, exames[0].alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    resultado = []
    for exame in exames:
        for linha in await listar_resultados_exame(db, utilizador, exame.id):
            resultado.append({**linha, "letra_variante": exame.letra_variante})
    return resultado


# ==========================================
# EXAMES — tentativa do aluno (usado a partir de cruds/portal.py)
# ==========================================
async def listar_exames_do_aluno(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID) -> list[dict]:
    """Exames iniciados para a turma atual do aluno, resolvidos para a
    variante atribuída a este aluno especificamente (ver
    LMSGrupoExameAtribuicao) — nunca expõe as variantes irmãs."""
    atribuicoes = {a.grupo_id: a.exame_id for a in (await db.execute(
        select(LMSGrupoExameAtribuicao).where(
            LMSGrupoExameAtribuicao.matricula_id == matricula_id, LMSGrupoExameAtribuicao.tenant_id == tenant_id
        )
    )).scalars().all()}

    linhas = (await db.execute(
        select(LMSExame, Disciplina.nome)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == LMSExame.alocacao_id)
        .join(Disciplina, Disciplina.id == ProfessorTurmaDisciplina.disciplina_id)
        .where(
            ProfessorTurmaDisciplina.turma_id == turma_id,
            LMSExame.tenant_id == tenant_id,
            LMSExame.publicado.is_(True),
            LMSExame.iniciado.is_(True)
        )
        .order_by(LMSExame.data_inicio.desc())
    )).all()

    # Cada grupo só pode contribuir a variante atribuída a este aluno
    # (ou nenhuma, se ainda não houver atribuição para ele) — nunca as irmãs.
    exames_do_aluno: dict[uuid.UUID, tuple[LMSExame, str]] = {}
    for exame, nome_disciplina in linhas:
        variante_atribuida = atribuicoes.get(exame.grupo_id)
        if variante_atribuida is None or variante_atribuida != exame.id:
            continue
        exames_do_aluno[exame.grupo_id] = (exame, nome_disciplina)

    tentativas = {t.exame_id: t for t in (await db.execute(
        select(LMSTentativaExame).where(LMSTentativaExame.matricula_id == matricula_id)
    )).scalars().all()}

    agora = datetime.now(timezone.utc)
    resultado = []
    for exame, nome_disciplina in exames_do_aluno.values():
        tentativa = tentativas.get(exame.id)
        if tentativa:
            status_tentativa = _derivar_status_tentativa(tentativa)
        else:
            status_tentativa = "NAO_INICIADA"
        dentro_da_janela = exame.data_inicio <= agora <= exame.data_fim
        resultado.append({
            "id": exame.id,
            "titulo": exame.titulo,
            "nome_disciplina": nome_disciplina,
            "data_inicio": exame.data_inicio,
            "data_fim": exame.data_fim,
            "duracao_minutos": exame.duracao_minutos,
            "modalidade": exame.modalidade,
            "status_tentativa": status_tentativa,
            "pode_iniciar": status_tentativa in ("NAO_INICIADA", "EM_CURSO") and dentro_da_janela,
            # Enquanto a aguardar correção, a nota está só parcialmente
            # calculada (falta pontuar as questões ABERTA) — não é
            # mostrada ainda, para não parecer a nota final ao aluno.
            "nota_obtida": tentativa.nota_obtida if tentativa and status_tentativa == "SUBMETIDA" else None,
            "nota_maxima": tentativa.nota_maxima if tentativa and status_tentativa == "SUBMETIDA" else None,
        })
    return resultado


async def _obter_exame_publicado_da_turma(db: AsyncSession, tenant_id, exame_id: uuid.UUID, turma_id: uuid.UUID, matricula_id: uuid.UUID) -> LMSExame:
    """Só devolve o exame se estiver publicado E iniciado (ver
    cruds/lms.py::iniciar_grupo_exame — publicado sozinho já não
    chega) e pertencer à turma do aluno — nunca deixa aceder a um
    exame de outra turma trocando o id no URL. Confirma ainda, via
    LMSGrupoExameAtribuicao, que esta é mesmo a variante atribuída a
    este aluno — tentar a variante de um colega dá o mesmo 404 de
    "não encontrado", nunca revela que existe outra."""
    exame = (await db.execute(
        select(LMSExame)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == LMSExame.alocacao_id)
        .where(
            LMSExame.id == exame_id, LMSExame.tenant_id == tenant_id,
            LMSExame.publicado.is_(True), LMSExame.iniciado.is_(True), ProfessorTurmaDisciplina.turma_id == turma_id
        )
    )).scalars().first()
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado.")

    atribuicao = (await db.execute(
        select(LMSGrupoExameAtribuicao).where(
            LMSGrupoExameAtribuicao.grupo_id == exame.grupo_id, LMSGrupoExameAtribuicao.matricula_id == matricula_id,
            LMSGrupoExameAtribuicao.tenant_id == tenant_id
        )
    )).scalars().first()
    if not atribuicao or atribuicao.exame_id != exame.id:
        raise HTTPException(status_code=404, detail="Exame não encontrado.")
    return exame


async def iniciar_tentativa(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID, exame_id: uuid.UUID) -> dict:
    exame = await _obter_exame_publicado_da_turma(db, tenant_id, exame_id, turma_id, matricula_id)
    agora = datetime.now(timezone.utc)
    if not (exame.data_inicio <= agora <= exame.data_fim):
        raise HTTPException(status_code=400, detail="Este exame não está disponível neste momento.")

    tentativa = (await db.execute(
        select(LMSTentativaExame).where(LMSTentativaExame.exame_id == exame_id, LMSTentativaExame.matricula_id == matricula_id)
    )).scalars().first()

    if tentativa:
        if tentativa.data_submissao:
            raise HTTPException(status_code=400, detail="Já submeteu este exame — não é possível repetir.")
        # Retoma a tentativa já em curso, com a MESMA ordem gerada da primeira vez (nunca gera uma nova).
        ordem_ids = tentativa.ordem_questoes
    else:
        linhas_questao = (await db.execute(
            select(LMSExameQuestao.questao_id).where(LMSExameQuestao.exame_id == exame_id).order_by(LMSExameQuestao.ordem)
        )).scalars().all()
        ordem_ids = [str(qid) for qid in linhas_questao]
        if exame.baralhar_perguntas:
            random.shuffle(ordem_ids)
        tentativa = LMSTentativaExame(
            tenant_id=tenant_id, exame_id=exame_id, matricula_id=matricula_id,
            ordem_questoes=ordem_ids, respostas={}
        )
        db.add(tentativa)
        await db.commit()
        await db.refresh(tentativa)

    questoes = {str(q.id): q for q in (await db.execute(
        select(LMSQuestao).where(LMSQuestao.id.in_(ordem_ids))
    )).scalars().all()}

    return {
        "tentativa_id": tentativa.id,
        "titulo": exame.titulo,
        "data_inicio_tentativa": tentativa.data_inicio,
        "duracao_minutos": exame.duracao_minutos,
        # Nunca inclui resposta_correta aqui — só depois de submeter (ver obter_resultado_tentativa).
        "perguntas": [
            {"id": qid, "enunciado": questoes[qid].enunciado, "tipo": questoes[qid].tipo, "opcoes": questoes[qid].opcoes}
            for qid in ordem_ids if qid in questoes
        ],
        "respostas_ja_dadas": tentativa.respostas,
    }


async def registar_evento_suspeito(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID, exame_id: uuid.UUID) -> int:
    """
    Proctoring básico (Page Visibility API): o frontend chama isto cada
    vez que o aluno sai da aba/janela durante uma tentativa em curso —
    a deteção em si vive só no browser (ver features/portal), este
    endpoint só regista a contagem para o professor rever ao corrigir
    (ver listar_resultados_exame). Nunca bloqueia nem invalida a
    tentativa — é só sinal, a decisão fica sempre com um humano.
    """
    await _obter_exame_publicado_da_turma(db, tenant_id, exame_id, turma_id, matricula_id)

    tentativa = (await db.execute(
        select(LMSTentativaExame).where(LMSTentativaExame.exame_id == exame_id, LMSTentativaExame.matricula_id == matricula_id)
    )).scalars().first()
    if not tentativa or tentativa.data_submissao:
        # Tentativa inexistente ou já fechada — nada a registar (o
        # aluno pode ter mudado de aba depois de sair do exame; não é
        # um erro que valha a pena reportar ao frontend).
        return tentativa.eventos_suspeitos if tentativa else 0

    tentativa.eventos_suspeitos += 1
    await db.commit()
    await db.refresh(tentativa)
    return tentativa.eventos_suspeitos


async def _notificar_exame_corrigido(db: AsyncSession, tenant_id, exame: LMSExame, matricula_id: uuid.UUID, tentativa: LMSTentativaExame) -> None:
    """Avisa o aluno (e o(s) responsável(is) com login, se existirem) que
    a prova foi corrigida e qual a nota — mesmo padrão de null-guard já
    usado em cruds/documentos.py e cruds/financeiro.py (nem todo o Aluno/
    Responsavel tem usuario_id/login próprio)."""
    from app.database.models_pessoas import AlunoResponsavel, ResponsavelFinanceiroLegal

    linha = (await db.execute(
        select(Aluno.usuario_id).join(Matricula, Matricula.aluno_id == Aluno.id).where(Matricula.id == matricula_id)
    )).first()
    usuario_ids = {linha[0]} if linha and linha[0] else set()

    responsaveis = (await db.execute(
        select(ResponsavelFinanceiroLegal.usuario_id)
        .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
        .join(Matricula, Matricula.aluno_id == AlunoResponsavel.aluno_id)
        .where(Matricula.id == matricula_id, ResponsavelFinanceiroLegal.usuario_id.is_not(None))
    )).scalars().all()
    usuario_ids.update(responsaveis)

    mensagem = f'A sua nota em "{exame.titulo}" é {tentativa.nota_obtida} / {tentativa.nota_maxima}.'
    for usuario_id in usuario_ids:
        await crud_notificacoes.criar_notificacao(
            db, tenant_id, usuario_id, tipo="EXAME_CORRIGIDO",
            titulo=f'Exame corrigido: "{exame.titulo}"', mensagem=mensagem, link="/portal?tab=pauta"
        )


async def submeter_tentativa(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID, exame_id: uuid.UUID, dados: LMSSubmeterTentativa) -> dict:
    exame = await _obter_exame_publicado_da_turma(db, tenant_id, exame_id, turma_id, matricula_id)

    tentativa = (await db.execute(
        select(LMSTentativaExame).where(LMSTentativaExame.exame_id == exame_id, LMSTentativaExame.matricula_id == matricula_id)
    )).scalars().first()
    if not tentativa:
        raise HTTPException(status_code=400, detail="Ainda não iniciou este exame.")
    if tentativa.data_submissao:
        raise HTTPException(status_code=400, detail="Já submeteu este exame.")

    questoes = {str(q.id): q for q in (await db.execute(
        select(LMSQuestao).where(LMSQuestao.id.in_(tentativa.ordem_questoes))
    )).scalars().all()}

    nota_obtida = Decimal("0.00")
    nota_maxima = Decimal("0.00")
    tem_questao_aberta = False
    for qid in tentativa.ordem_questoes:
        questao = questoes.get(qid)
        if not questao:
            continue  # questão entretanto apagada — não deveria acontecer (apagar_questao bloqueia se usada), mas não deixa a correção rebentar
        nota_maxima += questao.valor
        if questao.tipo == "ABERTA":
            tem_questao_aberta = True
            continue  # sem pontuação ainda — fica a aguardar corrigir_tentativa
        if dados.respostas.get(qid) == questao.resposta_correta:
            nota_obtida += questao.valor

    tentativa.respostas = dados.respostas
    tentativa.nota_obtida = nota_obtida  # parcial quando há ABERTA pendente — só as questões objetivas já contam
    tentativa.nota_maxima = nota_maxima  # inclui o valor das ABERTA mesmo antes de corrigidas
    tentativa.data_submissao = datetime.now(timezone.utc)
    tentativa.corrigida_finalizada = not tem_questao_aberta
    await db.commit()
    await db.refresh(tentativa)

    # Se este exame estiver ligado a uma Avaliacao do Diário (ver
    # criar_grupo_exame), escala a nota para a escala de notas da
    # escola (Tenant.nota_maxima) e alimenta NotaAvaliacao/RegistroNota
    # — exames antigos sem avaliacao_id continuam a corrigir
    # automaticamente sem este passo (ver docstring de LMSExame.avaliacao_id).
    # Só quando corrigida_finalizada: uma tentativa com ABERTA pendente
    # só entra no Diário depois de corrigir_tentativa a finalizar, para
    # não aparecer uma nota parcial "fantasma" na pauta antes da hora.
    if exame.avaliacao_id and nota_maxima > 0 and tentativa.corrigida_finalizada:
        nota_maxima_tenant_raw = (await db.execute(select(Tenant.nota_maxima).where(Tenant.id == tenant_id))).scalar_one()
        nota_maxima_tenant = Decimal(str(nota_maxima_tenant_raw))
        valor_escalado = (nota_obtida / nota_maxima * nota_maxima_tenant).quantize(Decimal("0.01"))
        await crud_diario.lancar_nota_avaliacao_individual(db, tenant_id, exame.avaliacao_id, matricula_id, valor_escalado)

    if tentativa.corrigida_finalizada:
        await _notificar_exame_corrigido(db, tenant_id, exame, matricula_id, tentativa)

    return {"nota_obtida": tentativa.nota_obtida, "nota_maxima": tentativa.nota_maxima, "corrigida_finalizada": tentativa.corrigida_finalizada}


async def corrigir_tentativa(db: AsyncSession, utilizador: dict, exame_id: uuid.UUID, matricula_id: uuid.UUID, dados: LMSCorrigirTentativaInput) -> dict:
    """Corrige questões ABERTA pendentes (dados.correcoes) e/ou
    sobrescreve/finaliza diretamente o total (dados.nota_obtida_override)
    de uma tentativa — o segundo caso aplica-se mesmo a uma tentativa já
    corrigida_finalizada=True, cobrindo "prova presencial, o professor
    corrige sempre" sem precisar de um fluxo à parte. RBAC: RN01 —
    Professor só na sua própria alocação, Gestor/Secretaria em qualquer."""
    tenant_id = utilizador["tenant_id"]
    exame = await _obter_exame(db, tenant_id, exame_id)
    alocacao = await _obter_alocacao(db, tenant_id, exame.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    tentativa = (await db.execute(
        select(LMSTentativaExame).where(
            LMSTentativaExame.exame_id == exame_id, LMSTentativaExame.matricula_id == matricula_id, LMSTentativaExame.tenant_id == tenant_id
        )
    )).scalars().first()
    if not tentativa or not tentativa.data_submissao:
        raise HTTPException(status_code=400, detail="Este aluno ainda não submeteu este exame.")

    questoes = {str(q.id): q for q in (await db.execute(
        select(LMSQuestao).where(LMSQuestao.id.in_(tentativa.ordem_questoes))
    )).scalars().all()}

    if dados.correcoes:
        correcoes_atuais = dict(tentativa.correcoes_manuais)
        for item in dados.correcoes:
            qid = str(item.questao_id)
            questao = questoes.get(qid)
            if not questao or questao.tipo != "ABERTA":
                raise HTTPException(status_code=400, detail=f"Questão {qid} não é uma questão de resposta aberta desta tentativa.")
            if item.pontos > questao.valor:
                raise HTTPException(status_code=400, detail=f"Pontos fora do intervalo (0 a {questao.valor}) para a questão {qid}.")
            correcoes_atuais[qid] = {"pontos": str(item.pontos), "comentario": item.comentario}
        tentativa.correcoes_manuais = correcoes_atuais

    # Recalcula o total: soma das objetivas certas + soma dos pontos
    # manuais já atribuídos às ABERTA (as ainda não corrigidas contam 0).
    nota_calculada = Decimal("0.00")
    todas_abertas_corrigidas = True
    for qid in tentativa.ordem_questoes:
        questao = questoes.get(qid)
        if not questao:
            continue
        if questao.tipo == "ABERTA":
            correcao = tentativa.correcoes_manuais.get(qid)
            if correcao:
                nota_calculada += Decimal(correcao["pontos"])
            else:
                todas_abertas_corrigidas = False
        elif tentativa.respostas.get(qid) == questao.resposta_correta:
            nota_calculada += questao.valor

    tentativa.nota_obtida = dados.nota_obtida_override if dados.nota_obtida_override is not None else nota_calculada
    # Override explícito OU já não resta nenhuma ABERTA por corrigir => finalizada.
    tentativa.corrigida_finalizada = dados.nota_obtida_override is not None or todas_abertas_corrigidas
    tentativa.corrigido_por_usuario_id = utilizador["usuario_id"]
    tentativa.corrigido_em = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tentativa)

    if exame.avaliacao_id and tentativa.nota_maxima and tentativa.nota_maxima > 0 and tentativa.corrigida_finalizada:
        nota_maxima_tenant_raw = (await db.execute(select(Tenant.nota_maxima).where(Tenant.id == tenant_id))).scalar_one()
        nota_maxima_tenant = Decimal(str(nota_maxima_tenant_raw))
        valor_escalado = (tentativa.nota_obtida / tentativa.nota_maxima * nota_maxima_tenant).quantize(Decimal("0.01"))
        await crud_diario.lancar_nota_avaliacao_individual(
            db, tenant_id, exame.avaliacao_id, matricula_id, valor_escalado, usuario_id=utilizador["usuario_id"]
        )

    if tentativa.corrigida_finalizada:
        await _notificar_exame_corrigido(db, tenant_id, exame, matricula_id, tentativa)

    return {"nota_obtida": tentativa.nota_obtida, "nota_maxima": tentativa.nota_maxima, "corrigida_finalizada": tentativa.corrigida_finalizada}


async def obter_resultado_tentativa(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, exame_id: uuid.UUID) -> dict:
    """Resultado + gabarito — só chamado depois de a tentativa estar
    submetida. Para ESCOLHA_MULTIPLA/VERDADEIRO_FALSO, mostrar a
    resposta certa aqui não compromete a integridade do exame (correção
    automática já feita). Para ABERTA, resposta_correta é só uma dica
    de correção para o staff e NUNCA é devolvida ao aluno — em vez
    disso devolve pontos_obtidos/comentario (None enquanto não corrigida)."""
    tentativa = (await db.execute(
        select(LMSTentativaExame).where(
            LMSTentativaExame.exame_id == exame_id, LMSTentativaExame.matricula_id == matricula_id, LMSTentativaExame.tenant_id == tenant_id
        )
    )).scalars().first()
    if not tentativa or not tentativa.data_submissao:
        raise HTTPException(status_code=404, detail="Ainda não submeteu este exame.")

    questoes = {str(q.id): q for q in (await db.execute(
        select(LMSQuestao).where(LMSQuestao.id.in_(tentativa.ordem_questoes))
    )).scalars().all()}

    perguntas = []
    for qid in tentativa.ordem_questoes:
        questao = questoes.get(qid)
        if not questao:
            continue
        if questao.tipo == "ABERTA":
            correcao = tentativa.correcoes_manuais.get(qid)
            perguntas.append({
                "id": qid, "enunciado": questao.enunciado, "tipo": questao.tipo, "opcoes": [],
                "resposta_correta": None,
                "resposta_dada": tentativa.respostas.get(qid),
                "correta": None,
                "pontos_obtidos": Decimal(correcao["pontos"]) if correcao else None,
                "comentario": correcao["comentario"] if correcao else None,
            })
        else:
            perguntas.append({
                "id": qid, "enunciado": questao.enunciado, "tipo": questao.tipo, "opcoes": questao.opcoes,
                "resposta_correta": questao.resposta_correta,
                "resposta_dada": tentativa.respostas.get(qid),
                "correta": tentativa.respostas.get(qid) == questao.resposta_correta,
                "pontos_obtidos": None,
                "comentario": None,
            })

    return {
        "nota_obtida": tentativa.nota_obtida,
        "nota_maxima": tentativa.nota_maxima,
        "data_submissao": tentativa.data_submissao,
        "corrigida_finalizada": tentativa.corrigida_finalizada,
        "perguntas": perguntas,
    }
