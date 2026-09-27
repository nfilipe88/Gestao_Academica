"""Schemas Pydantic do Módulo Académico (Curso, Série/Ano, Turma, Disciplina, Grade Curricular)."""
from datetime import datetime
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


class CursoOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    site_publico_visivel: bool
    site_publico_descricao: Optional[str] = None


class SerieAnoOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    curso_id: uuid.UUID
    nome: str


class TurmaOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    serie_ano_id: uuid.UUID
    nome_codigo: str
    ano_letivo: int
    vagas_maximas: int


class DisciplinaOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    carga_horaria_total: Optional[int] = None


class GradeCurricularOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    serie_ano_id: uuid.UUID
    disciplina_id: uuid.UUID


class ObjetivoAprendizagemOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    disciplina_id: uuid.UUID
    nome: str
    descricao: Optional[str] = None
    data_criacao: datetime
