import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TipoCalendario = Literal["PERIODO_LETIVO", "AVALIACOES", "EXAMES", "EXAMES_FINAIS", "EXAMES_RECURSO", "OUTRO"]


class CalendarioCreate(BaseModel):
    ano_letivo: int = Field(ge=2000, le=2100)
    tipo: TipoCalendario
    nome: str = Field(min_length=2, max_length=120)
    data_inicio: date
    data_fim: date
    observacoes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _datas(self):
        if self.data_inicio > self.data_fim:
            raise ValueError("A data de início não pode ser depois da data de fim.")
        return self


class CalendarioUpdate(BaseModel):
    tipo: TipoCalendario | None = None
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    data_inicio: date | None = None
    data_fim: date | None = None
    observacoes: str | None = Field(default=None, max_length=500)


class CalendarioOut(BaseModel):
    # None nas entradas vindas do Diário (só leitura — editam-se em Diário de Classe)
    id: uuid.UUID | None = None
    ano_letivo: int
    tipo: str
    nome: str
    data_inicio: date | None
    data_fim: date | None
    observacoes: str | None = None
    origem: Literal["CALENDARIO", "DIARIO"] = "CALENDARIO"
    # Estado face a hoje: DECORRER, PROXIMO ou TERMINADO — calculado, nunca gravado.
    estado: str | None = None

    model_config = {"from_attributes": True}
