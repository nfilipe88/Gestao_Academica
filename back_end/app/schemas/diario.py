"""Schemas Pydantic do Diário de Classe (frequência, notas, períodos de avaliação)."""
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
import uuid


class FrequenciaAluno(BaseModel):
    matricula_id: uuid.UUID
    presenca: bool
    faltas: int = 0


class FrequenciaLoteCreate(BaseModel):
    data_aula: date
    quantidade_aulas: int = 1
    conteudo_programado: str | None = None
    frequencias: list[FrequenciaAluno]


class NotaAluno(BaseModel):
    matricula_id: uuid.UUID
    valor_nota: Decimal


class NotaLoteCreate(BaseModel):
    periodo_avaliacao: str
    tipo_avaliacao: str | None = None
    data_avaliacao: date | None = None
    notas: list[NotaAluno]


class PeriodoAvaliacaoCreate(BaseModel):
    nome: str
