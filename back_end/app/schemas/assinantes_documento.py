"""Atribuição de quem assina cada tipo de documento formal — ver
app/database/models.py::AssinanteDocumento e app/core/assinaturas.py.
Distinto da assinatura PESSOAL (app/schemas/perfil.py, self-service): aqui
é o Gestor a decidir, por tipo de documento, QUEM assina — a imagem em si
continua a vir sempre da assinatura pessoal (AssinaturaUsuario) dessa
pessoa.
"""
import uuid

from pydantic import BaseModel, Field, field_validator

# Os 5 tipos de documento que passam pelo bloco de assinatura do envelope
# comum (ver documentos_pdf.py::_ENVELOPE) — CARTAO_ACESSO (crachá) e OUTRO
# não têm bloco de assinatura, ficam de fora de propósito.
TIPOS_DOCUMENTO_ASSINAVEL = {"CERTIFICADO", "DECLARACAO", "HISTORICO_ESCOLAR", "BOLETIM", "RECIBO"}


class AssinanteDocumentoOut(BaseModel):
    id: uuid.UUID
    tipo_documento: str
    usuario_id: uuid.UUID
    nome_usuario: str
    cargo: str
    ordem: int
    model_config = {"from_attributes": True}


class AssinanteDocumentoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    tipo_documento: str
    usuario_id: uuid.UUID
    cargo: str = Field(..., min_length=1, max_length=255)
    ordem: int = 0

    @field_validator("tipo_documento")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in TIPOS_DOCUMENTO_ASSINAVEL:
            raise ValueError(f"Tipo de documento inválido. Use um de: {', '.join(sorted(TIPOS_DOCUMENTO_ASSINAVEL))}.")
        return v


class AssinanteDocumentoUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    cargo: str = Field(..., min_length=1, max_length=255)
    ordem: int = 0
