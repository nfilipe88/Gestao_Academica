import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class SitePublicoFoto(Base):
    """Galeria de fotos da página pública da escola (ver
    app/database/models.py::Tenant.site_publico_* e
    app/api/v1/publico.py::obter_site_publico). Só a chave no storage
    (app/core/storage.py) — a imagem em si nunca fica exposta como URL
    direta do bucket, o endpoint público lê o ficheiro e devolve-o como
    data URI, mesma técnica já usada para o logótipo nos PDFs (ver
    storage.obter_logo_data_uri)."""
    __tablename__ = "site_publico_foto"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    chave_storage: Mapped[str] = mapped_column(String(500), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
