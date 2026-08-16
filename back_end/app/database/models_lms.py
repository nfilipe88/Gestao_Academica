"""LMS mínimo: materiais de aula publicados pelo professor, por
turma+disciplina. É o conteúdo sobre o qual o aluno pode pedir ajuda ao
Prof. Virtual (ver app/core/prof_virtual.py) — o botão de ajuda vive
sempre "dentro" de um material, nunca solto, para a IA ter contexto
real do que o aluno está a estudar.
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class MaterialAula(Base):
    __tablename__ = "material_aula"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)  # Ex: "Equações do 2º Grau"
    corpo: Mapped[str] = mapped_column(Text, nullable=False)  # conteúdo em texto simples — sem anexos/multimédia nesta primeira versão

    # Opcional: liga ao catálogo de Fase 2 (ver models_academico.py) —
    # dá ao Prof. Virtual e ao relatório de Indicadores um vocabulário
    # comum para o mesmo tópico.
    objetivo_aprendizagem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objetivo_aprendizagem.id", ondelete="SET NULL"), nullable=True
    )

    publicado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # False = rascunho, aluno não vê

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
