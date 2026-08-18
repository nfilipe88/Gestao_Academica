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

from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, Professor
from app.database.models_diario import ProfessorTurmaDisciplina
from app.database.models_lms import LMSExame, LMSExameQuestao, LMSQuestao, LMSTentativaExame, MaterialAula
from app.core import prof_virtual
from app.schemas.lms import (
    LMSExameCreate, LMSQuestaoCreate, LMSQuestaoUpdate, LMSSubmeterTentativa,
    MaterialAulaCreate, MaterialAulaUpdate, SugestaoConteudoCreate
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


async def listar_exames(db: AsyncSession, utilizador: dict, alocacao_id: uuid.UUID) -> list[LMSExame]:
    tenant_id = utilizador["tenant_id"]
    alocacao = await _obter_alocacao(db, tenant_id, alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    return (await db.execute(
        select(LMSExame)
        .where(LMSExame.alocacao_id == alocacao_id, LMSExame.tenant_id == tenant_id)
        .order_by(LMSExame.data_inicio.desc())
    )).scalars().all()


async def criar_exame(db: AsyncSession, utilizador: dict, dados: LMSExameCreate) -> LMSExame:
    tenant_id = utilizador["tenant_id"]
    alocacao = await _obter_alocacao(db, tenant_id, dados.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    questoes = (await db.execute(
        select(LMSQuestao).where(LMSQuestao.id.in_(dados.questao_ids), LMSQuestao.tenant_id == tenant_id)
    )).scalars().all()
    if len(questoes) != len(dados.questao_ids):
        raise HTTPException(status_code=404, detail="Uma ou mais questões não foram encontradas na sua instituição.")
    if any(q.disciplina_id != alocacao.disciplina_id for q in questoes):
        raise HTTPException(status_code=400, detail="Todas as questões têm de ser da disciplina desta alocação.")

    novo_exame = LMSExame(
        tenant_id=tenant_id,
        alocacao_id=dados.alocacao_id,
        titulo=dados.titulo.strip(),
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        duracao_minutos=dados.duracao_minutos,
        baralhar_perguntas=dados.baralhar_perguntas,
        publicado=False,
        criado_por_usuario_id=utilizador["usuario_id"]
    )
    db.add(novo_exame)
    await db.flush()  # obter o id do exame sem ainda fechar a transação

    for ordem, questao_id in enumerate(dados.questao_ids):
        db.add(LMSExameQuestao(tenant_id=tenant_id, exame_id=novo_exame.id, questao_id=questao_id, ordem=ordem))

    await db.commit()
    await db.refresh(novo_exame)
    return novo_exame


async def alternar_publicacao_exame(db: AsyncSession, utilizador: dict, exame_id: uuid.UUID, publicado: bool) -> LMSExame:
    tenant_id = utilizador["tenant_id"]
    exame = await _obter_exame(db, tenant_id, exame_id)
    alocacao = await _obter_alocacao(db, tenant_id, exame.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    exame.publicado = publicado
    await db.commit()
    await db.refresh(exame)
    return exame


async def apagar_exame(db: AsyncSession, utilizador: dict, exame_id: uuid.UUID) -> None:
    tenant_id = utilizador["tenant_id"]
    exame = await _obter_exame(db, tenant_id, exame_id)
    alocacao = await _obter_alocacao(db, tenant_id, exame.alocacao_id)
    await _validar_autoria_alocacao(db, utilizador, alocacao)

    ja_tem_tentativa = (await db.execute(
        select(LMSTentativaExame).where(LMSTentativaExame.exame_id == exame_id)
    )).scalars().first()
    if ja_tem_tentativa:
        raise HTTPException(status_code=400, detail="Este exame já tem tentativas de alunos — não pode ser apagado (pode despublicá-lo).")

    await db.delete(exame)
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
        "perguntas": [
            {
                "id": questao.id, "enunciado": questao.enunciado, "tipo": questao.tipo,
                "opcoes": questao.opcoes, "resposta_correta": questao.resposta_correta, "valor": questao.valor,
            }
            for _, questao in linhas
        ],
    }


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
            "status": "SUBMETIDA" if tentativa.data_submissao else "EM_CURSO",
            "nota_obtida": tentativa.nota_obtida,
            "nota_maxima": tentativa.nota_maxima,
            "eventos_suspeitos": tentativa.eventos_suspeitos,
            "data_inicio": tentativa.data_inicio,
            "data_submissao": tentativa.data_submissao,
        }
        for tentativa, nome_aluno in linhas
    ]


# ==========================================
# EXAMES — tentativa do aluno (usado a partir de cruds/portal.py)
# ==========================================
async def listar_exames_do_aluno(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID) -> list[dict]:
    """Exames publicados para a turma atual do aluno, com o estado da sua própria tentativa (se existir)."""
    linhas = (await db.execute(
        select(LMSExame, Disciplina.nome)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == LMSExame.alocacao_id)
        .join(Disciplina, Disciplina.id == ProfessorTurmaDisciplina.disciplina_id)
        .where(
            ProfessorTurmaDisciplina.turma_id == turma_id,
            LMSExame.tenant_id == tenant_id,
            LMSExame.publicado.is_(True)
        )
        .order_by(LMSExame.data_inicio.desc())
    )).all()

    tentativas = {t.exame_id: t for t in (await db.execute(
        select(LMSTentativaExame).where(LMSTentativaExame.matricula_id == matricula_id)
    )).scalars().all()}

    agora = datetime.now(timezone.utc)
    resultado = []
    for exame, nome_disciplina in linhas:
        tentativa = tentativas.get(exame.id)
        if tentativa:
            status_tentativa = "SUBMETIDA" if tentativa.data_submissao else "EM_CURSO"
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
            "status_tentativa": status_tentativa,
            "pode_iniciar": status_tentativa in ("NAO_INICIADA", "EM_CURSO") and dentro_da_janela,
            "nota_obtida": tentativa.nota_obtida if tentativa else None,
            "nota_maxima": tentativa.nota_maxima if tentativa else None,
        })
    return resultado


async def _obter_exame_publicado_da_turma(db: AsyncSession, tenant_id, exame_id: uuid.UUID, turma_id: uuid.UUID) -> LMSExame:
    """Só devolve o exame se estiver publicado e pertencer à turma do aluno — nunca deixa aceder a um exame de outra turma trocando o id no URL."""
    exame = (await db.execute(
        select(LMSExame)
        .join(ProfessorTurmaDisciplina, ProfessorTurmaDisciplina.id == LMSExame.alocacao_id)
        .where(
            LMSExame.id == exame_id, LMSExame.tenant_id == tenant_id,
            LMSExame.publicado.is_(True), ProfessorTurmaDisciplina.turma_id == turma_id
        )
    )).scalars().first()
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado.")
    return exame


async def iniciar_tentativa(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID, exame_id: uuid.UUID) -> dict:
    exame = await _obter_exame_publicado_da_turma(db, tenant_id, exame_id, turma_id)
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


async def submeter_tentativa(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, turma_id: uuid.UUID, exame_id: uuid.UUID, dados: LMSSubmeterTentativa) -> dict:
    await _obter_exame_publicado_da_turma(db, tenant_id, exame_id, turma_id)

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
    for qid in tentativa.ordem_questoes:
        questao = questoes.get(qid)
        if not questao:
            continue  # questão entretanto apagada — não deveria acontecer (apagar_questao bloqueia se usada), mas não deixa a correção rebentar
        nota_maxima += questao.valor
        if dados.respostas.get(qid) == questao.resposta_correta:
            nota_obtida += questao.valor

    tentativa.respostas = dados.respostas
    tentativa.nota_obtida = nota_obtida
    tentativa.nota_maxima = nota_maxima
    tentativa.data_submissao = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tentativa)

    return {"nota_obtida": tentativa.nota_obtida, "nota_maxima": tentativa.nota_maxima}


async def obter_resultado_tentativa(db: AsyncSession, tenant_id, matricula_id: uuid.UUID, exame_id: uuid.UUID) -> dict:
    """Resultado + gabarito completo — só chamado depois de a tentativa estar submetida, por isso mostrar a resposta certa aqui não compromete a integridade do exame."""
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

    return {
        "nota_obtida": tentativa.nota_obtida,
        "nota_maxima": tentativa.nota_maxima,
        "data_submissao": tentativa.data_submissao,
        "perguntas": [
            {
                "id": qid, "enunciado": questoes[qid].enunciado, "tipo": questoes[qid].tipo, "opcoes": questoes[qid].opcoes,
                "resposta_correta": questoes[qid].resposta_correta,
                "resposta_dada": tentativa.respostas.get(qid),
                "correta": tentativa.respostas.get(qid) == questoes[qid].resposta_correta,
            }
            for qid in tentativa.ordem_questoes if qid in questoes
        ],
    }
