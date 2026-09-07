import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class Comunicado(Base):
    """Comunicado/Convocatória enviado a Turma, Aluno ou toda a Escola.

    Guarda um registo histórico do que foi enviado (quem, quando, para
    quem, quantos destinatários) — o envio em si (e-mails individuais)
    é feito em background e não fica aqui, só a contagem.
    """
    __tablename__ = "comunicado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    tipo: Mapped[str] = mapped_column(String(20), nullable=False) # COMUNICADO, CONVOCATORIA
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)

    destinatario_tipo: Mapped[str] = mapped_column(String(20), nullable=False) # TURMA, ALUNO, ESCOLA
    destinatario_turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="SET NULL"), nullable=True)
    destinatario_aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="SET NULL"), nullable=True)

    total_destinatarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_envio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class RespostaComunicado(Base):
    """Resposta de um encarregado/aluno a um Comunicado, escrita no Portal
    (ver app/cruds/portal.py::responder_comunicado_do_educando e
    app/api/v1/portal.py) — uma única thread por Comunicado, partilhada por
    todos os que respondem (um Comunicado para TURMA/ESCOLA pode ter várias
    respostas de encarregados diferentes), por isso cada linha regista
    aluno_id + autor_nome para a escola distinguir quem disse o quê.

    tenant_id desnormalizado (repetido do Comunicado pai) — mesmo padrão de
    TicketMensagem (models_suporte.py): a policy de RLS filtra esta tabela
    diretamente, sem depender de um JOIN ao Comunicado. Aqui é sempre
    NOT NULL (ao contrário de TicketMensagem.tenant_id) porque uma resposta
    só existe vinda de um login autenticado já ligado a um tenant — não há
    caso anónimo, ao contrário dos tickets de suporte."""
    __tablename__ = "resposta_comunicado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    comunicado_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comunicado.id", ondelete="CASCADE"), nullable=False, index=True)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    autor_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    autor_nome: Mapped[str] = mapped_column(String(255), nullable=False)  # snapshot — mesmo motivo de TicketMensagem.autor_nome
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class AnexoComunicacao(Base):
    """Ficheiro anexado a um Comunicado/Convocatória (ex.: circular em
    PDF, imagem) — o conteúdo em si vive no storage (app/core/storage.py,
    S3-compatível ou disco local), aqui só a referência e os metadados
    para listagem/download autenticado (ver app/api/v1/comunicacoes.py)."""
    __tablename__ = "anexo_comunicacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    comunicado_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comunicado.id", ondelete="CASCADE"), nullable=False)

    chave_storage: Mapped[str] = mapped_column(String(500), nullable=False)
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
