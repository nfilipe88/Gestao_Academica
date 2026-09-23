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
TIPOS_QUESTAO_VALIDOS = {"ESCOLHA_MULTIPLA", "VERDADEIRO_FALSO", "ABERTA"}


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
        elif self.tipo == "ABERTA":
            # Sem correção automática — resposta_correta fica como dica
            # de correção opcional só para o staff (nunca mostrada ao
            # aluno), ver cruds/lms.py::corrigir_tentativa.
            self.opcoes = []
            self.resposta_correta = self.resposta_correta or ""
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
# EXAMES (motor online) — um GRUPO de 1+ variantes (Variante A/B/C,
# perguntas genuinamente diferentes, não só ordem baralhada), ligado
# desde a criação a uma Avaliacao do Diário (ver cruds/lms.py::criar_grupo_exame).
# ==========================================
MODALIDADES_VALIDAS = {"PRESENCIAL", "REMOTO"}


class LMSVarianteInput(BaseModel):
    """Uma variante dentro do grupo — mesma janela/duração/modalidade
    do grupo, mas o seu próprio conjunto de perguntas. letra_variante
    em branco é atribuída pela ordem (A, B, C...)."""
    letra_variante: str | None = None
    questao_ids: list[uuid.UUID]

    @model_validator(mode="after")
    def _validar(self):
        if not self.questao_ids:
            raise ValueError("Cada variante precisa de pelo menos uma questão.")
        if len(set(self.questao_ids)) != len(self.questao_ids):
            raise ValueError("Não repita a mesma questão na mesma variante.")
        return self


class LMSGrupoExameCreate(BaseModel):
    alocacao_id: uuid.UUID
    titulo: str
    data_inicio: datetime
    data_fim: datetime
    duracao_minutos: int
    baralhar_perguntas: bool = True
    modalidade: str = "PRESENCIAL"
    # Cria a Avaliacao que recebe as notas — reaproveita o catálogo já
    # existente do Diário (ver cruds/diario.py::criar_avaliacao).
    periodo_avaliacao: str
    tipo_avaliacao: str
    peso: Decimal = Decimal("100")
    variantes: list[LMSVarianteInput]

    @model_validator(mode="after")
    def _validar(self):
        if not self.titulo.strip():
            raise ValueError("titulo é obrigatório.")
        if self.data_fim <= self.data_inicio:
            raise ValueError("data_fim tem de ser depois de data_inicio.")
        if self.duracao_minutos <= 0:
            raise ValueError("duracao_minutos tem de ser maior que zero.")
        if self.modalidade not in MODALIDADES_VALIDAS:
            raise ValueError(f"modalidade inválida. Use um de: {', '.join(sorted(MODALIDADES_VALIDAS))}.")
        if not self.variantes:
            raise ValueError("É preciso pelo menos uma variante.")
        letras = [v.letra_variante or chr(ord("A") + i) for i, v in enumerate(self.variantes)]
        if len(set(letras)) != len(letras):
            raise ValueError("Letras de variante repetidas.")
        return self


class LMSReatribuirVarianteInput(BaseModel):
    matricula_id: uuid.UUID
    exame_id: uuid.UUID  # a variante de destino — tem de pertencer ao mesmo grupo


class LMSSubmeterTentativa(BaseModel):
    respostas: dict[str, str]  # {questao_id (str): resposta dada}


class LMSCorrecaoQuestaoInput(BaseModel):
    """Pontos atribuídos manualmente a UMA questão ABERTA de uma tentativa."""
    questao_id: uuid.UUID
    pontos: Decimal
    comentario: str | None = None


class LMSCorrigirTentativaInput(BaseModel):
    """Corrige questões ABERTA pendentes (`correcoes`) e/ou sobrescreve/
    finaliza diretamente o total de uma tentativa (`nota_obtida_override`)
    — o segundo caso cobre "prova presencial, o professor corrige
    sempre", mesmo numa tentativa já 100% corrigida automaticamente
    (ver cruds/lms.py::corrigir_tentativa). Pelo menos um dos dois tem
    de vir preenchido."""
    correcoes: list[LMSCorrecaoQuestaoInput] = []
    nota_obtida_override: Decimal | None = None

    @model_validator(mode="after")
    def _validar(self):
        if not self.correcoes and self.nota_obtida_override is None:
            raise ValueError("Indique pelo menos uma correção de questão ou nota_obtida_override.")
        if self.nota_obtida_override is not None and self.nota_obtida_override < 0:
            raise ValueError("nota_obtida_override não pode ser negativo.")
        for item in self.correcoes:
            if item.pontos < 0:
                raise ValueError("pontos não pode ser negativo.")
        return self


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
