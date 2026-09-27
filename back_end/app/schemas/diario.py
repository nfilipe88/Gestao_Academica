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
    model_config = {"extra": "forbid"}
    data_aula: date
    quantidade_aulas: int = 1
    conteudo_programado: str | None = None
    frequencias: list[FrequenciaAluno]


class NotaAluno(BaseModel):
    matricula_id: uuid.UUID
    valor_nota: Decimal


class NotaLoteCreate(BaseModel):
    model_config = {"extra": "forbid"}
    periodo_avaliacao: str
    tipo_avaliacao: str | None = None
    data_avaliacao: date | None = None
    notas: list[NotaAluno]


class PeriodoAvaliacaoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str
    # Janela calendárica opcional — distinta do trancamento
    # (aberto/data_fecho, ver models_diario.py::PeriodoAvaliacao). Pode
    # ser preenchida já aqui ou mais tarde via PeriodoAvaliacaoJanelaUpdate.
    data_inicio: date | None = None
    data_fim: date | None = None


class PeriodoAvaliacaoJanelaUpdate(BaseModel):
    """Edita só a janela calendárica (data_inicio/data_fim) de um
    período já criado — nunca mexe em aberto/data_fecho (ver PATCH
    .../trancar e .../reabrir, que continuam a ser os únicos donos
    desses dois campos)."""
    model_config = {"extra": "forbid"}
    data_inicio: date | None = None
    data_fim: date | None = None


# ==========================================
# NOTA DE EXAME NACIONAL (NEN) — valor externo lançado à mão pelo
# Gestor/Secretaria, ver models_diario.py::NotaExameNacional.
# ==========================================
class NotaExameNacionalAluno(BaseModel):
    matricula_id: uuid.UUID
    valor_nota: Decimal


class NotaExameNacionalLoteCreate(BaseModel):
    model_config = {"extra": "forbid"}
    notas: list[NotaExameNacionalAluno]


# ==========================================
# AVALIAÇÕES (provas e contínuas) — ver models_diario.py::Avaliacao
# ==========================================
class AvaliacaoCreate(BaseModel):
    model_config = {"extra": "forbid"}
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
    model_config = {"extra": "forbid"}
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
    model_config = {"extra": "forbid"}
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
    model_config = {"extra": "forbid"}
    notas: list[NotaAvaliacaoAluno]
