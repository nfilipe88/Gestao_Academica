"""Tabelas de apoio ao Painel de Indicadores (BI) que precisam de persistência —
ao contrário do resto de cruds/indicadores.py, que é só agregação
on-the-fly sem gravar nada."""
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class TrilhaRecuperacao(Base):
    """Um plano de recuperação gerado por IA (Prof. Virtual) para um aluno
    sinalizado pelo motor de risco de evasão (ver
    cruds/indicadores.py::obter_risco_evasao).

    Persistido — ao contrário do resto do Painel de Indicadores, que é
    só agregação on-the-fly — por dois motivos: (1) histórico, para o
    Gestor ver o que já foi sugerido antes de gerar outra vez; (2)
    custo, para não chamar a API da Anthropic de novo sem necessidade
    sempre que a página é recarregada.
    """
    __tablename__ = "trilha_recuperacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    gerada_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    # Fotografia do risco no momento em que a trilha foi gerada — o
    # score em si nunca é persistido no motor de risco (é sempre
    # recalculado on-demand), mas aqui faz sentido guardar o valor que
    # motivou esta trilha específica, para dar contexto ao histórico.
    pontuacao_risco_momento: Mapped[int] = mapped_column(Integer, nullable=False)
    nivel_risco_momento: Mapped[str] = mapped_column(String(10), nullable=False)

    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
