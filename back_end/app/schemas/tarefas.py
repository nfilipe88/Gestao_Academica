"""Schemas Pydantic de Trabalhos/Tarefas."""
from pydantic import BaseModel, model_validator
from datetime import date
from decimal import Decimal
import uuid


class TarefaCreate(BaseModel):
    alocacao_id: uuid.UUID
    titulo: str
    descricao: str | None = None
    data_entrega: date
    valor_maximo: Decimal = Decimal("10.00")
    periodo_avaliacao: str | None = None  # opcional — RN03, mesmo período gerido em Diário

    @model_validator(mode="after")
    def _validar(self):
        if not self.titulo.strip():
            raise ValueError("titulo é obrigatório.")
        if self.valor_maximo <= 0:
            raise ValueError("valor_maximo tem de ser maior que zero.")
        return self


class AvaliacaoAlunoInput(BaseModel):
    matricula_id: uuid.UUID
    status: str  # ENTREGUE, ENTREGUE_ATRASADO, NAO_ENTREGUE
    nota: Decimal | None = None
    observacoes: str | None = None


class AvaliarTarefaLote(BaseModel):
    avaliacoes: list[AvaliacaoAlunoInput]
