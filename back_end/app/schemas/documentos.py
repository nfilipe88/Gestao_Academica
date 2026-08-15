import uuid
from decimal import Decimal

from pydantic import BaseModel


class PrecoDocumentoUpdate(BaseModel):
    preco: Decimal
    ativo: bool = True


class SolicitacaoDocumentoEmissaoCreate(BaseModel):
    tipo_documento: str
    formato_entrega: str = "DIGITAL"
    descricao_outro: str | None = None
    # Só necessário quando quem pede é RESPONSAVEL com mais de um educando.
    aluno_id: uuid.UUID | None = None


class CapturarPagamentoDocumentoRequest(BaseModel):
    order_id: str


class EntregarFisicoRequest(BaseModel):
    observacoes: str | None = None


class SolicitacaoDocumentoEscolaCreate(BaseModel):
    destinatario_tipo: str  # ALUNO, RESPONSAVEL, PROFESSOR
    destinatario_id: uuid.UUID  # aluno_id/responsavel_id/professor_id, conforme o tipo
    titulo: str
    descricao: str


class ResponderSolicitacaoEscolaRequest(BaseModel):
    resposta_texto: str
