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
from decimal import Decimal
from pydantic import BaseModel


class SitePublicoFotoOut(BaseModel):
    id: uuid.UUID
    url: str  # data URI — ver storage.py
    model_config = {"from_attributes": True}


class CursoPublicoOut(BaseModel):
    """Um curso publicado na página pública — só os que o Gestor marcou
    como visíveis (ver Curso.site_publico_visivel em
    app/database/models_academico.py), nunca todos os cursos da escola."""
    id: uuid.UUID
    nome: str
    descricao: str | None  # conteúdo programático, texto livre


class SitePublicoConfigOut(BaseModel):
    """Para o Gestor gerir em Configurações — inclui `ativo` mesmo
    quando ainda não há nada preenchido, ao contrário da versão pública."""
    ativo: bool
    slug: str | None
    template: str
    missao: str | None
    metodologia: str | None
    facebook: str | None
    instagram: str | None
    whatsapp: str | None
    fotos: list[SitePublicoFotoOut] = []


class SitePublicoConfigUpdate(BaseModel):
    ativo: bool
    slug: str | None = None
    template: str = "classico"
    missao: str | None = None
    metodologia: str | None = None
    facebook: str | None = None
    instagram: str | None = None
    whatsapp: str | None = None


class SitePublicoOut(BaseModel):
    """Resposta pública (sem autenticação) — só existe/responde quando
    `ativo=True` no Tenant; nunca inclui nada que não seja
    deliberadamente pensado para ser público (sem NIF, sem IBAN, sem
    contagens internas)."""
    tenant_id: uuid.UUID
    nome_fantasia: str
    template: str
    logotipo: str | None  # data URI, None = sem logótipo
    missao: str | None
    metodologia: str | None
    telefone_contacto: str | None
    email_contacto: str | None
    morada: str | None
    cidade: str | None
    facebook: str | None
    instagram: str | None
    whatsapp: str | None
    cursos: list[CursoPublicoOut] = []
    fotos: list[str] = []  # data URIs
    moeda: str
    # Valor da taxa de matrícula (encargo único) — None = escola não cobra.
    # Publicado de propósito (tal como os preços/cursos acima): uma
    # família candidata-se a saber já quanto vai custar a matrícula em
    # si, não só as mensalidades. Ver Tenant.valor_taxa_matricula.
    valor_taxa_matricula: Decimal | None
