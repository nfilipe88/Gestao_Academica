"""Schemas Pydantic da grade horária (Horários)."""
from pydantic import BaseModel, model_validator
from datetime import time
import uuid


class HorarioAulaCreate(BaseModel):
    alocacao_id: uuid.UUID
    dia_semana: int  # 1=Segunda ... 7=Domingo
    hora_inicio: time
    hora_fim: time
    sala: str | None = None

    @model_validator(mode="after")
    def _validar_intervalo(self):
        if not (1 <= self.dia_semana <= 7):
            raise ValueError("dia_semana deve estar entre 1 (Segunda) e 7 (Domingo).")
        if self.hora_fim <= self.hora_inicio:
            raise ValueError("hora_fim tem de ser depois de hora_inicio.")
        return self


class HorarioAulaUpdate(BaseModel):
    dia_semana: int | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    sala: str | None = None

    @model_validator(mode="after")
    def _validar_intervalo(self):
        if self.dia_semana is not None and not (1 <= self.dia_semana <= 7):
            raise ValueError("dia_semana deve estar entre 1 (Segunda) e 7 (Domingo).")
        if self.hora_inicio is not None and self.hora_fim is not None and self.hora_fim <= self.hora_inicio:
            raise ValueError("hora_fim tem de ser depois de hora_inicio.")
        return self
