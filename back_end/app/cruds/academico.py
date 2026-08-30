"""
Acesso a dados e regras de negócio do Módulo Académico (Curso, Série/Ano,
Turma, Disciplina, Grade Curricular).

Cada função recebe já o tenant_id resolvido (extraído do JWT na camada
de API) e o valida explicitamente em todas as queries — o RLS do
Postgres é a última linha de defesa, não a única (mesmo padrão de
sempre neste projeto). Erros de validação (404/400) são levantados
aqui como HTTPException para manter as rotas em app/api/v1/academico.py
finas — não há uma camada extra de exceções de domínio, dado o
tamanho do projeto.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.database.models_academico import Curso, Disciplina, GradeCurricular, ObjetivoAprendizagem, SerieAno, Turma
from app.schemas.academico import (
    CursoCreate, CursoSitePublicoUpdate, CursoUpdate, DisciplinaCreate, GradeCurricularCreate,
    ObjetivoAprendizagemCreate, SerieAnoCreate, TurmaCreate
)


# ==========================================
# CURSOS
# ==========================================
async def criar_curso(db: AsyncSession, tenant_id, dados: CursoCreate) -> Curso:
    novo_curso = Curso(nome=dados.nome, tenant_id=tenant_id)
    db.add(novo_curso)
    await db.commit()
    await db.refresh(novo_curso)
    return novo_curso


async def listar_cursos(db: AsyncSession, tenant_id) -> list[Curso]:
    resultado = await db.execute(select(Curso).where(Curso.tenant_id == tenant_id))
    return resultado.scalars().all()


async def _obter_curso(db: AsyncSession, tenant_id, curso_id) -> Curso:
    curso = (await db.execute(
        select(Curso).where(Curso.id == curso_id, Curso.tenant_id == tenant_id)
    )).scalars().first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")
    return curso


async def atualizar_curso(db: AsyncSession, tenant_id, curso_id, dados: CursoUpdate) -> Curso:
    curso = await _obter_curso(db, tenant_id, curso_id)
    curso.nome = dados.nome.strip()
    await db.commit()
    await db.refresh(curso)
    return curso


async def atualizar_curso_site_publico(db: AsyncSession, tenant_id, curso_id, dados: CursoSitePublicoUpdate) -> Curso:
    curso = await _obter_curso(db, tenant_id, curso_id)
    curso.site_publico_visivel = dados.visivel
    curso.site_publico_descricao = (dados.descricao or "").strip() or None
    await db.commit()
    await db.refresh(curso)
    return curso


# ==========================================
# SÉRIES/ANOS
# ==========================================
async def criar_serie_ano(db: AsyncSession, tenant_id, dados: SerieAnoCreate) -> SerieAno:
    curso_db = await db.execute(
        select(Curso).where(Curso.id == dados.curso_id, Curso.tenant_id == tenant_id)
    )
    if not curso_db.scalars().first():
        raise HTTPException(status_code=404, detail="Curso não encontrado na sua instituição.")

    nova_serie = SerieAno(curso_id=dados.curso_id, nome=dados.nome, tenant_id=tenant_id)
    db.add(nova_serie)
    await db.commit()
    await db.refresh(nova_serie)
    return nova_serie


async def listar_series(db: AsyncSession, tenant_id, curso_id: Optional[uuid.UUID] = None) -> list[SerieAno]:
    query = select(SerieAno).where(SerieAno.tenant_id == tenant_id)
    if curso_id:
        query = query.where(SerieAno.curso_id == curso_id)
    resultado = await db.execute(query)
    return resultado.scalars().all()


# ==========================================
# TURMAS
# ==========================================
async def criar_turma(db: AsyncSession, tenant_id, dados: TurmaCreate) -> Turma:
    # Filtro explícito, não só o RLS — mesma lógica aplicada em listar_cursos/listar_turmas.
    serie_db = await db.execute(
        select(SerieAno).where(SerieAno.id == dados.serie_ano_id, SerieAno.tenant_id == tenant_id)
    )
    if not serie_db.scalars().first():
        raise HTTPException(status_code=404, detail="Série/Ano não encontrada na sua instituição.")

    nova_turma = Turma(
        tenant_id=tenant_id,
        serie_ano_id=dados.serie_ano_id,
        nome_codigo=dados.nome_codigo,
        ano_letivo=dados.ano_letivo,
        vagas_maximas=dados.vagas_maximas
    )
    db.add(nova_turma)
    await db.commit()
    return nova_turma


async def listar_turmas(db: AsyncSession, tenant_id) -> list[Turma]:
    resultado = await db.execute(select(Turma).where(Turma.tenant_id == tenant_id))
    return resultado.scalars().all()


# ==========================================
# DISCIPLINAS
# ==========================================
async def criar_disciplina(db: AsyncSession, tenant_id, dados: DisciplinaCreate) -> Disciplina:
    nova_disciplina = Disciplina(
        tenant_id=tenant_id,
        nome=dados.nome,
        carga_horaria_total=dados.carga_horaria_total
    )
    db.add(nova_disciplina)
    await db.commit()
    await db.refresh(nova_disciplina)
    return nova_disciplina


async def listar_disciplinas(db: AsyncSession, tenant_id) -> list[Disciplina]:
    resultado = await db.execute(select(Disciplina).where(Disciplina.tenant_id == tenant_id))
    return resultado.scalars().all()


# ==========================================
# GRADE CURRICULAR (Série/Ano <-> Disciplina)
# ==========================================
async def adicionar_disciplina_a_serie(db: AsyncSession, tenant_id, dados: GradeCurricularCreate) -> GradeCurricular:
    serie = (await db.execute(
        select(SerieAno).where(SerieAno.id == dados.serie_ano_id, SerieAno.tenant_id == tenant_id)
    )).scalars().first()
    if not serie:
        raise HTTPException(status_code=404, detail="Série/Ano não encontrada na sua instituição.")

    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == dados.disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")

    ja_existe = (await db.execute(
        select(GradeCurricular).where(
            GradeCurricular.serie_ano_id == dados.serie_ano_id,
            GradeCurricular.disciplina_id == dados.disciplina_id
        )
    )).scalars().first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Esta disciplina já está associada a esta série/ano.")

    novo_item = GradeCurricular(
        tenant_id=tenant_id,
        serie_ano_id=dados.serie_ano_id,
        disciplina_id=dados.disciplina_id
    )
    db.add(novo_item)
    await db.commit()
    return novo_item


async def listar_grade_curricular(db: AsyncSession, tenant_id, serie_ano_id: Optional[uuid.UUID] = None) -> list[GradeCurricular]:
    query = select(GradeCurricular).where(GradeCurricular.tenant_id == tenant_id)
    if serie_ano_id:
        query = query.where(GradeCurricular.serie_ano_id == serie_ano_id)
    resultado = await db.execute(query)
    return resultado.scalars().all()


# ==========================================
# OBJETIVOS DE APRENDIZAGEM (catálogo por disciplina)
# ==========================================
# Ex.: em "Ciências" — "Células", "Sistema Solar". Cada Avaliacao (ver
# cruds/diario.py) pode apontar para um destes, para o Painel de
# Indicadores conseguir agregar desempenho por tópico, não só por
# disciplina inteira.
async def criar_objetivo_aprendizagem(db: AsyncSession, tenant_id, dados: ObjetivoAprendizagemCreate) -> ObjetivoAprendizagem:
    disciplina = (await db.execute(
        select(Disciplina).where(Disciplina.id == dados.disciplina_id, Disciplina.tenant_id == tenant_id)
    )).scalars().first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")

    novo_objetivo = ObjetivoAprendizagem(
        tenant_id=tenant_id,
        disciplina_id=dados.disciplina_id,
        nome=dados.nome.strip(),
        descricao=dados.descricao
    )
    db.add(novo_objetivo)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um objetivo de aprendizagem com este nome nesta disciplina.")
    await db.refresh(novo_objetivo)
    return novo_objetivo


async def listar_objetivos_aprendizagem(db: AsyncSession, tenant_id, disciplina_id: Optional[uuid.UUID] = None) -> list[ObjetivoAprendizagem]:
    query = select(ObjetivoAprendizagem).where(ObjetivoAprendizagem.tenant_id == tenant_id)
    if disciplina_id:
        query = query.where(ObjetivoAprendizagem.disciplina_id == disciplina_id)
    resultado = await db.execute(query.order_by(ObjetivoAprendizagem.nome))
    return resultado.scalars().all()
