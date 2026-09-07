"""Área de Eventos da escola (ex.: festa junina, feira de ciências) —
ver app/database/models_eventos.py::Evento/EventoFoto. Distinto do
Site Público (app/schemas/site_publico.py): aquele é uma galeria única
sem título/data/descrição, capada a 8 fotos; aqui cada evento tem os
seus próprios título/data/descrição e várias fotos, sem limite."""
import uuid
from datetime import date
from pydantic import BaseModel


class EventoFotoOut(BaseModel):
    id: uuid.UUID
    url: str  # data URI — ver storage.py
    model_config = {"from_attributes": True}


class EventoCreate(BaseModel):
    titulo: str
    data: date
    descricao: str | None = None
    publicado: bool = True


class EventoUpdate(BaseModel):
    titulo: str | None = None
    data: date | None = None
    descricao: str | None = None
    publicado: bool | None = None


class EventoOut(BaseModel):
    """Para o Gestor gerir na página de Eventos — inclui eventos ainda
    não publicados, ao contrário de EventoPublicoOut."""
    id: uuid.UUID
    titulo: str
    data: date
    descricao: str | None
    publicado: bool
    fotos: list[EventoFotoOut] = []


class EventoPublicoOut(BaseModel):
    """Resposta pública (sem autenticação, embutida em SitePublicoOut) —
    só eventos publicado=True chegam aqui."""
    id: uuid.UUID
    titulo: str
    data: date
    descricao: str | None
    fotos: list[str] = []  # data URIs
