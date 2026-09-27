"""Schemas Pydantic do Painel de Indicadores (BI) — só a Trilha de
Recuperação (TrilhaRecuperacao) é um registo ORM próprio; o resto do
painel (/indicadores, /risco-evasao) é um agregado calculado à parte,
já montado à mão em cruds/indicadores.py, não um schema de saída."""
from datetime import datetime
import uuid

from pydantic import BaseModel


class TrilhaRecuperacaoOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    aluno_id: uuid.UUID
    matricula_id: uuid.UUID
    gerada_por: uuid.UUID | None = None
    pontuacao_risco_momento: int
    nivel_risco_momento: str
    conteudo: str
    data_criacao: datetime
