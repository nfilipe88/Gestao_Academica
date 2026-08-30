"""Página pública de apresentação de uma escola (marketing/angariação
de alunos) — ver app/database/models.py::Tenant.site_publico_* e
app/database/models_site_publico.py::SitePublicoFoto.

Distinto de app/schemas/publico.py (apresenta a PLATAFORMA em si a
quem procura uma solução de gestão escolar) — aqui é cada ESCOLA já
cliente a apresentar-se a famílias interessadas em matricular os
filhos.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class SitePublicoFotoOut(BaseModel):
    id: uuid.UUID
    url: str  # data URI — ver storage.py
    model_config = {"from_attributes": True}


class SitePublicoConfigOut(BaseModel):
    """Para o Gestor gerir em Configurações — inclui `ativo` mesmo
    quando ainda não há nada preenchido, ao contrário da versão pública."""
    ativo: bool
    missao: str | None
    metodologia: str | None
    fotos: list[SitePublicoFotoOut] = []


class SitePublicoConfigUpdate(BaseModel):
    ativo: bool
    missao: str | None = None
    metodologia: str | None = None


class SitePublicoOut(BaseModel):
    """Resposta pública (sem autenticação) — só existe/responde quando
    `ativo=True` no Tenant; nunca inclui nada que não seja
    deliberadamente pensado para ser público (sem NIF, sem IBAN, sem
    contagens internas)."""
    tenant_id: uuid.UUID
    nome_fantasia: str
    logotipo: str | None  # data URI, None = sem logótipo
    missao: str | None
    metodologia: str | None
    telefone_contacto: str | None
    email_contacto: str | None
    morada: str | None
    cidade: str | None
    cursos: list[str] = []
    fotos: list[str] = []  # data URIs
