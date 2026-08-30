"""Schemas Pydantic do Módulo Académico (Curso, Série/Ano, Turma, Disciplina, Grade Curricular)."""
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class CursoCreate(BaseModel):
    nome: str


class CursoUpdate(BaseModel):
    nome: str = Field(min_length=1, max_length=150)


class CursoSitePublicoUpdate(BaseModel):
    """Presença e conteúdo programático deste curso na página pública
    da escola — ver app/schemas/site_publico.py::CursoPublicoOut."""
    visivel: bool
    descricao: str | None = None


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
