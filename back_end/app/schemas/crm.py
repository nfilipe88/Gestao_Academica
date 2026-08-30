"""Schemas Pydantic do CRM (Lead, Funil, Oportunidade)."""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
from decimal import Decimal
import uuid


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


class LeadStaffCreate(_NormalizaEmailOpcional):
    """Criação manual por um utilizador autenticado (ex: contacto presencial/telefónico) — já entra direto no funil, ao contrário do POST público que só cria o Lead+Oportunidade sem mais nada."""
    nome_responsavel: str
    email_contato: EmailStr | None = None
    telefone: str | None = None
    nome_aluno_candidato: str
    data_nascimento_candidato: date | None = None
    curso_interesse_id: uuid.UUID | None = None
    origem_lead: str = "PRESENCIAL"


class LeadUpdate(_NormalizaEmailOpcional):
    nome_responsavel: str | None = None
    email_contato: EmailStr | None = None
    telefone: str | None = None
    nome_aluno_candidato: str | None = None
    data_nascimento_candidato: date | None = None
    curso_interesse_id: uuid.UUID | None = None


class EtapaCreate(BaseModel):
    ordem: int
    nome_etapa: str
    eh_etapa_ganho: bool = False


class OportunidadeCreate(BaseModel):
    lead_id: uuid.UUID
    valor_estimado_anual: Decimal | None = None
    data_fecho_prevista: date | None = None
    turma_interesse_id: uuid.UUID | None = None


class OportunidadeUpdate(BaseModel):
    """Completar a oportunidade antes (ou depois) de ganhar — em particular
    a Turma pretendida, que é o que falta à RN01 para também gerar
    Matrícula + Contrato Financeiro automaticamente."""
    valor_estimado_anual: Decimal | None = None
    data_fecho_prevista: date | None = None
    turma_interesse_id: uuid.UUID | None = None


class OportunidadeMover(BaseModel):
    nova_etapa_id: uuid.UUID
