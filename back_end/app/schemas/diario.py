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


# ==========================================
# AVALIAÇÕES (provas e contínuas) — ver models_diario.py::Avaliacao
# ==========================================
class AvaliacaoCreate(BaseModel):
    periodo_avaliacao: str
    titulo: str
    tipo_avaliacao: str  # "CONTINUA" | "PROVA"
    peso: Decimal = Decimal("100")
    data_avaliacao: date | None = None
    objetivo_aprendizagem_id: uuid.UUID | None = None


class AvaliacaoUpdate(BaseModel):
    titulo: str
    tipo_avaliacao: str
    peso: Decimal
    data_avaliacao: date | None = None
    objetivo_aprendizagem_id: uuid.UUID | None = None


class NotaAvaliacaoAluno(BaseModel):
    matricula_id: uuid.UUID
    valor_nota: Decimal


class NotaAvaliacaoLoteCreate(BaseModel):
    notas: list[NotaAvaliacaoAluno]
