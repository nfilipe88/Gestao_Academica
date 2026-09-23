"""
Importação de Dados Legados (mini-pauta MININED) — ver
app/cruds/importacao.py para a orquestração completa.

LoteImportacao regista cada confirmação de importação (uma turma+
disciplina+ano letivo por ficheiro); LoteImportacaoAluno é o detalhe
por aluno, usado por desfazer_importacao para saber exatamente o que
apagar sem tocar em registos partilhados (Turma/Disciplina/
PeriodoAvaliacao/TipoAvaliacaoConfig/Avaliacao) que podem já estar em
uso por lançamentos manuais feitos logo a seguir — ver docstring de
desfazer_importacao.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class LoteImportacao(Base):
    __tablename__ = "lote_importacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    nome_ficheiro_original: Mapped[str] = mapped_column(String(255), nullable=False)
    chave_storage_ficheiro: Mapped[str] = mapped_column(String(500), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)
    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)

    total_alunos_criados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_alunos_reaproveitados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_notas_lancadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # CONCLUIDO | DESFEITO — ver cruds/importacao.py::desfazer_importacao.
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="CONCLUIDO")
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_desfeito: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    desfeito_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)


class LoteImportacaoAluno(Base):
    """Um aluno tocado por um LoteImportacao — o que permite a
    desfazer_importacao saber exatamente quais Matricula/Aluno apagar,
    sem arrastar nada mais."""
    __tablename__ = "lote_importacao_aluno"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    lote_importacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lote_importacao.id", ondelete="CASCADE"), nullable=False)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)

    # False = este aluno foi criado por este lote (candidato a apagar ao
    # desfazer); True = já existia e só foi matriculado/associado — o
    # Aluno em si nunca é apagado ao desfazer.
    aluno_pre_existente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # True quando data_nascimento ficou com o valor sentinela (aluno sem
    # data de nascimento na mini-pauta) — ver cruds/importacao.py.
    data_nascimento_estimada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("lote_importacao_id", "aluno_id", name="uq_lote_aluno"),
    )
