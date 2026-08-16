"""Schemas Pydantic do Diário de Classe (frequência, notas, períodos de avaliação)."""
from pydantic import BaseModel
from datetime import date, time
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
    tipo_avaliacao: str  # nome de um TipoAvaliacaoConfig ativo do tenant
    peso: Decimal = Decimal("100")
    data_avaliacao: date | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    sala: str | None = None
    data_limite_correcao: date | None = None
    objetivo_aprendizagem_id: uuid.UUID | None = None


class AvaliacaoUpdate(BaseModel):
    titulo: str
    tipo_avaliacao: str
    peso: Decimal
    data_avaliacao: date | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    sala: str | None = None
    data_limite_correcao: date | None = None
    objetivo_aprendizagem_id: uuid.UUID | None = None


class AvaliacaoAgendarGeralCreate(BaseModel):
    """Agendamento "Geral" (toda a escola) — ver cruds/diario.py::agendar_avaliacao_geral.
    Cria uma Avaliacao por cada turma+disciplina atualmente alocada, todas com a mesma data/hora/sala."""
    periodo_avaliacao: str
    titulo: str
    tipo_avaliacao: str
    peso: Decimal = Decimal("100")
    data_avaliacao: date
    hora_inicio: time
    hora_fim: time
    sala: str | None = None
    data_limite_correcao: date | None = None


class NotaAvaliacaoAluno(BaseModel):
    matricula_id: uuid.UUID
    valor_nota: Decimal


class NotaAvaliacaoLoteCreate(BaseModel):
    notas: list[NotaAvaliacaoAluno]
