"""
LMS mínimo: gestão de materiais de aula pelo professor/staff.

A leitura do lado do aluno (Portal) vive em cruds/portal.py — este
módulo só trata da autoria (quem pode publicar/editar/apagar um
material), seguindo a mesma RN01 já usada em cruds/diario.py e
cruds/tarefas.py: Gestor/Secretaria em qualquer turma, Professor só
nas turmas+disciplinas onde está alocado.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_pessoas import Professor
from app.database.models_diario import ProfessorTurmaDisciplina
from app.database.models_lms import MaterialAula
from app.core import prof_virtual
from app.schemas.lms import MaterialAulaCreate, MaterialAulaUpdate, SugestaoConteudoCreate


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
