"""Schemas Pydantic do LMS (materiais de aula, banco de questões, exames) e do Prof. Virtual."""
from pydantic import BaseModel, model_validator
from datetime import datetime
from decimal import Decimal
import uuid


class MaterialAulaCreate(BaseModel):
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
    titulo: str
    corpo: str
    objetivo_aprendizagem_id: uuid.UUID | None = None
    publicado: bool = True


class MaterialAulaUpdate(BaseModel):
    titulo: str
    corpo: str
    objetivo_aprendizagem_id: uuid.UUID | None = None
    publicado: bool = True


# ==========================================
# BANCO DE QUESTÕES
# ==========================================
TIPOS_QUESTAO_VALIDOS = {"ESCOLHA_MULTIPLA", "VERDADEIRO_FALSO"}


class _ValidaQuestao(BaseModel):
    """Regras partilhadas por Create/Update: por tipo de questão, o que conta como opções/resposta válidas."""
    @model_validator(mode="after")
    def _validar(self):
        if self.tipo not in TIPOS_QUESTAO_VALIDOS:
            raise ValueError(f"Tipo inválido. Use um de: {', '.join(sorted(TIPOS_QUESTAO_VALIDOS))}.")
        if not self.enunciado.strip():
            raise ValueError("enunciado é obrigatório.")
        if self.valor <= 0:
            raise ValueError("valor tem de ser maior que zero.")
        if self.tipo == "VERDADEIRO_FALSO":
            if self.resposta_correta not in ("VERDADEIRO", "FALSO"):
                raise ValueError('Para VERDADEIRO_FALSO, resposta_correta tem de ser "VERDADEIRO" ou "FALSO".')
            self.opcoes = []
        else:
            if len(self.opcoes) < 2:
                raise ValueError("ESCOLHA_MULTIPLA precisa de pelo menos 2 opções.")
            if self.resposta_correta not in [str(i) for i in range(len(self.opcoes))]:
                raise ValueError("resposta_correta tem de ser o índice (\"0\", \"1\"...) de uma das opções.")
        return self


class LMSQuestaoCreate(_ValidaQuestao):
    disciplina_id: uuid.UUID
    enunciado: str
    tipo: str
    opcoes: list[str] = []
    resposta_correta: str
    valor: Decimal = Decimal("1.00")


class LMSQuestaoUpdate(_ValidaQuestao):
    enunciado: str
    tipo: str
    opcoes: list[str] = []
    resposta_correta: str
    valor: Decimal = Decimal("1.00")


# ==========================================
# EXAMES (motor online)
# ==========================================
class LMSExameCreate(BaseModel):
    alocacao_id: uuid.UUID
    titulo: str
    data_inicio: datetime
    data_fim: datetime
    duracao_minutos: int
    baralhar_perguntas: bool = True
    questao_ids: list[uuid.UUID]

    @model_validator(mode="after")
    def _validar(self):
        if not self.titulo.strip():
            raise ValueError("titulo é obrigatório.")
        if self.data_fim <= self.data_inicio:
            raise ValueError("data_fim tem de ser depois de data_inicio.")
        if self.duracao_minutos <= 0:
            raise ValueError("duracao_minutos tem de ser maior que zero.")
        if not self.questao_ids:
            raise ValueError("Selecione pelo menos uma questão para o exame.")
        if len(set(self.questao_ids)) != len(self.questao_ids):
            raise ValueError("Não repita a mesma questão no exame.")
        return self


class LMSSubmeterTentativa(BaseModel):
    respostas: dict[str, str]  # {questao_id (str): resposta dada}


# ==========================================
# PROF. VIRTUAL — chat sem persistência em BD (ver app/core/prof_virtual.py)
# ==========================================
class MensagemProfVirtual(BaseModel):
    papel: str  # "aluno" | "assistente"
    texto: str


class ProfVirtualPerguntaCreate(BaseModel):
    material_id: uuid.UUID
    historico: list[MensagemProfVirtual] = []
    pergunta: str


# ==========================================
# PROF. VIRTUAL — sugestão de conteúdo para o professor (redação do material)
# ==========================================
class SugestaoConteudoCreate(BaseModel):
    turma_id: uuid.UUID
    disciplina_id: uuid.UUID
    titulo: str
    objetivo_aprendizagem_id: uuid.UUID | None = None
    instrucoes: str | None = None
