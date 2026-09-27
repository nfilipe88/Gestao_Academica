"""Schemas Pydantic do CRM (Lead, Funil, Oportunidade)."""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date, datetime
from decimal import Decimal
import uuid

from app.schemas.comum import DecimalComoFloat


class _NormalizaEmailOpcional(BaseModel):
    """
    Um formulário HTML envia "" (string vazia) quando um campo opcional
    fica em branco, não None — e EmailStr rejeita "" com um erro 422
    confuso ("must have an @-sign"). Normaliza para None antes da
    validação, para o campo continuar mesmo opcional na prática.
    """
    @field_validator("email_contato", mode="before", check_fields=False)
    @classmethod
    def _vazio_vira_none(cls, valor):
        return valor or None


class LeadPublicoCreate(_NormalizaEmailOpcional):
    model_config = {"extra": "forbid"}
    nome_responsavel: str
    email_contato: EmailStr | None = None
    telefone: str | None = None
    nome_aluno_candidato: str
    # Opcional aqui (mesmo raciocínio do LeadStaffCreate) — mas quando
    # vem preenchido já desbloqueia a conversão automática RN01, que
    # antes ficava sempre pendente de a Secretaria preencher isto à
    # mão (ver assistente de matrícula em features/public/matricula).
    data_nascimento_candidato: date | None = None
    curso_interesse_id: uuid.UUID | None = None
    origem_lead: str = "SITE"
    # Só relevante no assistente de matrícula (candidatura completa,
    # com documentos) — o formulário de contacto rápido não o mostra e
    # continua a enviar False, o que é correto para esse caso.
    aceitou_regulamento: bool = False
    # True só no assistente de matrícula (candidatura): fica recusada quando a
    # escola encerrou as matrículas. O contacto rápido (False) nunca é bloqueado.
    candidatura_matricula: bool = False
    # Mensagem livre e opcional deixada no formulário público — ver
    # LeadCandidato.mensagem.
    mensagem: str | None = None
    # Token do Google reCAPTCHA v3 (ver core/recaptcha.py) — opcional
    # aqui pela mesma razão de RegistoInicial.recaptcha_token.
    recaptcha_token: str | None = None


class LeadStaffCreate(_NormalizaEmailOpcional):
    """Criação manual por um utilizador autenticado (ex: contacto presencial/telefónico) — já entra direto no funil, ao contrário do POST público que só cria o Lead+Oportunidade sem mais nada."""
    model_config = {"extra": "forbid"}
    nome_responsavel: str
    email_contato: EmailStr | None = None
    telefone: str | None = None
    nome_aluno_candidato: str
    data_nascimento_candidato: date | None = None
    curso_interesse_id: uuid.UUID | None = None
    origem_lead: str = "PRESENCIAL"
    mensagem: str | None = None


class LeadUpdate(_NormalizaEmailOpcional):
    model_config = {"extra": "forbid"}
    nome_responsavel: str | None = None
    email_contato: EmailStr | None = None
    telefone: str | None = None
    nome_aluno_candidato: str | None = None
    data_nascimento_candidato: date | None = None
    curso_interesse_id: uuid.UUID | None = None


class EtapaCreate(BaseModel):
    model_config = {"extra": "forbid"}
    ordem: int
    nome_etapa: str
    eh_etapa_ganho: bool = False


class OportunidadeCreate(BaseModel):
    model_config = {"extra": "forbid"}
    lead_id: uuid.UUID
    valor_estimado_anual: Decimal | None = None
    data_fecho_prevista: date | None = None
    turma_interesse_id: uuid.UUID | None = None


class OportunidadeUpdate(BaseModel):
    """Completar a oportunidade antes (ou depois) de ganhar — em particular
    a Turma pretendida, que é o que falta à RN01 para também gerar
    Matrícula + Contrato Financeiro automaticamente."""
    model_config = {"extra": "forbid"}
    valor_estimado_anual: Decimal | None = None
    data_fecho_prevista: date | None = None
    turma_interesse_id: uuid.UUID | None = None


class OportunidadeMover(BaseModel):
    model_config = {"extra": "forbid"}
    nova_etapa_id: uuid.UUID


class MensagemLeadCreate(BaseModel):
    model_config = {"extra": "forbid"}
    corpo: str


class MensagemLeadOut(BaseModel):
    id: uuid.UUID
    autor_tipo: str
    autor_nome: str
    corpo: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class FunilEtapaOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    ordem: int
    nome_etapa: str
    eh_etapa_ganho: bool


class LeadCandidatoOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    curso_interesse_id: uuid.UUID | None = None
    nome_responsavel: str
    email_contato: str | None = None
    telefone: str | None = None
    nome_aluno_candidato: str
    data_nascimento_candidato: date | None = None
    mensagem: str | None = None
    origem_lead: str
    data_entrada: datetime
    aceitou_regulamento: bool


class LeadDocumentoOut(BaseModel):
    """Só metadados — nunca o conteúdo/data URI (ver
    cruds/crm.py::obter_documento_lead_url)."""
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tipo: str
    nome_original: str


class LeadCandidatoKanbanOut(BaseModel):
    """O Lead tal como embutido em cada cartão do Kanban de Oportunidades
    (ver cruds/crm.py::listar_oportunidades) — um subconjunto diferente
    de LeadCandidatoOut, montado à mão ali, não um from_attributes puro."""
    id: uuid.UUID
    nome_responsavel: str
    email_contato: str | None = None
    telefone: str | None = None
    nome_aluno_candidato: str
    data_nascimento_candidato: date | None = None
    origem_lead: str
    curso_interesse_id: uuid.UUID | None = None
    data_entrada: datetime
    aceitou_regulamento: bool
    mensagem: str | None = None
    documentos: list[LeadDocumentoOut]


class OportunidadeCRMOut(BaseModel):
    """A OportunidadeCRM "nua" (sem o Lead embutido) — devolvida por
    POST /crm/oportunidades. O Kanban em si (GET /crm/oportunidades) usa
    antes OportunidadeKanbanOut, com o lead lá dentro."""
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    lead_id: uuid.UUID
    etapa_id: uuid.UUID
    valor_estimado_anual: DecimalComoFloat | None = None
    data_fecho_prevista: date | None = None
    turma_interesse_id: uuid.UUID | None = None
    aluno_gerado_id: uuid.UUID | None = None
    responsavel_gerado_id: uuid.UUID | None = None
    data_criacao: datetime
    data_atualizacao: datetime


class OportunidadeMoverOut(BaseModel):
    """Resposta de PATCH .../oportunidades/{id}/mover — inclui a
    OportunidadeCRM atualizada (o frontend Angular não lê isto, só
    `mensagem`, mas os testes de integração da RN01 confirmam
    aluno_gerado_id por aqui: ver tests/test_crm.py)."""
    mensagem: str
    oportunidade: OportunidadeCRMOut
    aluno_gerado_id: uuid.UUID | None = None


class LeadCriadoOut(BaseModel):
    lead: LeadCandidatoOut
    oportunidade_id: uuid.UUID


class OportunidadeKanbanOut(BaseModel):
    """Uma oportunidade + o seu Lead, tal como devolvida pelo quadro
    Kanban (GET /crm/oportunidades) — ver cruds/crm.py::listar_oportunidades."""
    id: uuid.UUID
    etapa_id: uuid.UUID
    valor_estimado_anual: DecimalComoFloat | None = None
    data_fecho_prevista: date | None = None
    turma_interesse_id: uuid.UUID | None = None
    aluno_gerado_id: uuid.UUID | None = None
    data_criacao: datetime
    lead: LeadCandidatoKanbanOut
