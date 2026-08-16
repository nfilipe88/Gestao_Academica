"""Schemas Pydantic do LMS mínimo (materiais de aula) e do Prof. Virtual."""
from pydantic import BaseModel
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
