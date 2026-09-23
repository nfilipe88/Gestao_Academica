"""Schemas Pydantic da Importação de Dados Legados (mini-pauta MININED) — ver app/cruds/importacao.py."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, model_validator
import uuid


# ==========================================
# PRÉ-VISUALIZAÇÃO (resposta de POST /mini-pauta/preview — nada gravado na BD)
# ==========================================
class MetadadosDetectados(BaseModel):
    disciplina_nome: str | None = None
    sala: str | None = None
    turma_nome_codigo: str | None = None
    turno: str | None = None
    ano_letivo_raw: str | None = None
    ano_letivo: int | None = None
    chave_storage_ficheiro: str


class TrimestreDetectado(BaseModel):
    nome: str
    tem_dados: bool
    formula_mt_original: str | None = None
    peso_mact: Decimal
    peso_pt: Decimal
    peso_detectado_automaticamente: bool


class NotaTrimestreDetectada(BaseModel):
    mact: Decimal | None = None
    pt: Decimal | None = None


class AlunoDetectado(BaseModel):
    linha_excel: int
    numero_pauta: int | None = None
    nome_completo: str
    aluno_existente_id: uuid.UUID | None = None
    notas: dict[str, NotaTrimestreDetectada]
    anomalias: list[str] = []


class ResumoPreview(BaseModel):
    total_linhas: int
    total_com_anomalias: int
    total_correspondencias_nome_existente: int


class PreviewMiniPautaResposta(BaseModel):
    metadados: MetadadosDetectados
    trimestres: list[TrimestreDetectado]
    alunos: list[AlunoDetectado]
    resumo: ResumoPreview


# ==========================================
# CONFIRMAÇÃO (corpo de POST /mini-pauta/confirmar)
# ==========================================
class EntidadeRefOuNova(BaseModel):
    """Exatamente um dos dois: reaproveitar uma entidade já existente
    (id) ou criar uma nova com este nome — nunca os dois nem nenhum."""
    id: uuid.UUID | None = None
    nome_novo: str | None = None

    @model_validator(mode="after")
    def _validar_exclusividade(self):
        if bool(self.id) == bool(self.nome_novo):
            raise ValueError("Indique ou um id existente ou um nome_novo — nunca os dois nem nenhum.")
        return self


class TrimestreConfirmado(BaseModel):
    nome: str
    tem_dados: bool
    peso_mact: Decimal
    peso_pt: Decimal


class AlunoConfirmado(BaseModel):
    nome_completo: str
    acao: str  # "CRIAR_NOVO_ALUNO" | "REUTILIZAR_ALUNO_EXISTENTE"
    aluno_existente_id: uuid.UUID | None = None
    notas: dict[str, NotaTrimestreDetectada]


class ImportacaoMiniPautaConfirmar(BaseModel):
    curso: EntidadeRefOuNova
    serie_ano: EntidadeRefOuNova
    turma: EntidadeRefOuNova
    disciplina: EntidadeRefOuNova
    ano_letivo: int
    trimestres: list[TrimestreConfirmado]
    alunos: list[AlunoConfirmado]
    nome_ficheiro_original: str
    chave_storage_ficheiro: str


class ResumoImportacao(BaseModel):
    total_alunos_criados: int
    total_alunos_reaproveitados: int
    total_notas_lancadas: int


class ImportacaoMiniPautaResposta(BaseModel):
    lote_importacao_id: uuid.UUID
    estado: str
    resumo: ResumoImportacao
    alunos_com_data_nascimento_pendente: list[str]


class LoteImportacaoOut(BaseModel):
    id: uuid.UUID
    nome_ficheiro_original: str
    ano_letivo: int
    total_alunos_criados: int
    total_alunos_reaproveitados: int
    total_notas_lancadas: int
    estado: str
    data_criacao: datetime
    model_config = {"from_attributes": True}


class DesfazerImportacaoResposta(BaseModel):
    estado: str
    alunos_removidos: int
    alunos_mantidos: int
    mensagem: str
