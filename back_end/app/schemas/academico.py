"""Schemas Pydantic do Módulo Académico (Curso, Série/Ano, Turma, Disciplina, Grade Curricular)."""
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class CursoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str


class CursoUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str = Field(min_length=1, max_length=150)


class CursoSitePublicoUpdate(BaseModel):
    """Presença e conteúdo programático deste curso na página pública
    da escola — ver app/schemas/site_publico.py::CursoPublicoOut."""
    model_config = {"extra": "forbid"}
    visivel: bool
    descricao: str | None = None


class SerieAnoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    curso_id: uuid.UUID
    nome: str


class TurmaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    serie_ano_id: uuid.UUID
    nome_codigo: str
    ano_letivo: int
    vagas_maximas: int = 30


class DisciplinaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str
    carga_horaria_total: Optional[int] = None


class GradeCurricularCreate(BaseModel):
    model_config = {"extra": "forbid"}
    serie_ano_id: uuid.UUID
    disciplina_id: uuid.UUID


class ObjetivoAprendizagemCreate(BaseModel):
    model_config = {"extra": "forbid"}
    disciplina_id: uuid.UUID
    nome: str
    descricao: Optional[str] = None
