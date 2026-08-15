"""Schemas Pydantic do Módulo Académico (Curso, Série/Ano, Turma, Disciplina, Grade Curricular)."""
from pydantic import BaseModel
from typing import Optional
import uuid


class CursoCreate(BaseModel):
    nome: str


class SerieAnoCreate(BaseModel):
    curso_id: uuid.UUID
    nome: str


class TurmaCreate(BaseModel):
    serie_ano_id: uuid.UUID
    nome_codigo: str
    ano_letivo: int
    vagas_maximas: int = 30


class DisciplinaCreate(BaseModel):
    nome: str
    carga_horaria_total: Optional[int] = None


class GradeCurricularCreate(BaseModel):
    serie_ano_id: uuid.UUID
    disciplina_id: uuid.UUID


class ObjetivoAprendizagemCreate(BaseModel):
    disciplina_id: uuid.UUID
    nome: str
    descricao: Optional[str] = None
