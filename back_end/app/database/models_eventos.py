import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class Evento(Base):
    """Um evento da escola (ex.: festa junina, feira de ciências, dia
    aberto) — gerido pelo Gestor numa página própria (features/eventos)
    e publicado na página pública da escola (ver
    app/api/v1/publico.py::obter_site_publico, campo `eventos`).

    Distinto de propósito da galeria genérica de Site Público
    (SitePublicoFoto, sem título/data/descrição, capada a 8 fotos) —
    aqui cada evento tem o seu próprio título, data e várias fotos,
    sem limite artificial nenhum (ver EventoFoto/adicionar_foto_evento
    em cruds/eventos.py)."""
    __tablename__ = "evento"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    # Data de calendário mostrada ao público (não um timestamp de
    # auditoria, por isso Date e não DateTime — mesmo espírito de
    # RegistroComportamento.data_ocorrencia).
    data: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Permite à escola preparar um evento antes de o publicar, sem o
    # apagar/recriar depois — só eventos publicado=True aparecem no
    # endpoint público (ver listar_eventos_publicos).
    publicado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class EventoFoto(Base):
    """Fotos de um Evento — mesmo princípio de SitePublicoFoto (só a
    chave no storage, nunca uma URL direta do bucket), mas sem o limite
    de 8 fotos: um evento pode ter tantas fotos quantas fizerem
    sentido para contar a história desse dia."""
    __tablename__ = "evento_foto"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    evento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evento.id", ondelete="CASCADE"), nullable=False, index=True)

    chave_storage: Mapped[str] = mapped_column(String(500), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
