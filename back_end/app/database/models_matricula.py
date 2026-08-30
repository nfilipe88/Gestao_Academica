import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class Matricula(Base):
    """O vínculo do Aluno com a Escola, numa Turma, num ano letivo.

    RN04 do documento de arquitetura: toda nova matrícula recebe
    status_matricula "ATIVO" automaticamente. As transições (Trancado,
    Transferido, Evadido, Ciclo Concluído) são feitas via PATCH
    /matriculas/{id}/status, nunca escritas diretamente na criação.

    CICLO_CONCLUIDO ("Fim de Ciclo", ver app/cruds/matriculas.py) é
    distinto de desativar o login do aluno: fecha o vínculo académico
    desta matrícula com a escola (o aluno foi para uma escola fora da
    plataforma, ou concluiu a escolaridade), mas o acesso ao Portal só
    é revogado se alguém desativar o Usuario explicitamente — são
    decisões independentes.
    """
    __tablename__ = "matricula"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)

    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)
    status_matricula: Mapped[str] = mapped_column(String(20), nullable=False, default="ATIVO") # ATIVO, TRANSFERIDO, TRANCADO, EVADIDO, CICLO_CONCLUIDO
    # Motivo da transição de estado mais recente — sobretudo relevante
    # em CICLO_CONCLUIDO (TRANSFERENCIA_EXTERNA, CONCLUSAO_ESCOLARIDADE,
    # OUTRO — ver MOTIVOS_FIM_CICLO_VALIDOS), mas guarda o motivo de
    # qualquer transição (o schema MatriculaStatusUpdate já previa este
    # campo; só não estava a ser persistido).
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_matricula: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # RN03 - Prevenção de Duplicidade
        UniqueConstraint("aluno_id", "turma_id", "ano_letivo", name="uq_matricula_aluno_turma_ano"),
        # "Matrículas ativas de um aluno/de uma turma" é a consulta mais
        # comum sobre esta tabela (transferências, boletim, financeiro,
        # portal) — cobre o filtro completo em vez de só tenant_id.
        Index("ix_matricula_tenant_status", "tenant_id", "status_matricula"),
    )


class MatriculaDocumento(Base):
    """Documento de apoio anexado a uma matrícula pela Secretaria/Gestor
    — sobretudo usado no Reingresso (aluno que volta de uma escola fora
    da plataforma, tipicamente para "outra classe": o comprovativo de
    habilitações da escola anterior justifica em que série entra), mas
    não é exclusivo disso — qualquer matrícula pode ter documentos de
    apoio anexados. Só a chave no storage (app/core/storage.py), nunca
    um URL direto do bucket — mesmo princípio de SitePublicoFoto/
    LeadDocumento."""
    __tablename__ = "matricula_documento"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False, index=True)

    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ex.: "Certificado de habilitações — Escola X"
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    chave_storage: Mapped[str] = mapped_column(String(500), nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class PedidoRematricula(Base):
    """Confirmação de interesse do encarregado/aluno, via Portal, em
    renovar a matrícula para o ano letivo seguinte ("rematrícula
    self-service" — ver app/cruds/portal.py::pedir_rematricula).

    NÃO cria a Matrícula do ano seguinte por si só — quem decide a
    turma de destino continua a ser a Secretaria/Gestor (implica
    progressão de série, uma decisão pedagógica, não administrativa).
    Isto só sinaliza à escola que a família já confirmou intenção,
    para priorizar no ecrã de Rematrícula (ver
    cruds/matriculas.py::listar_candidatos_rematricula) — o mesmo
    bloqueio de RN05 (mensalidade em atraso de ano anterior) aplicado
    em criar_matricula também se aplica aqui, antes de aceitar o pedido.
    """
    __tablename__ = "pedido_rematricula"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    matricula_atual_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    ano_letivo_destino: Mapped[int] = mapped_column(Integer, nullable=False)
    solicitado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    data_solicitacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Um único pedido por aluno/ano de destino — clicar duas vezes
        # não duplica (pedir_rematricula trata isso como idempotente).
        UniqueConstraint("aluno_id", "ano_letivo_destino", name="uq_pedido_rematricula_aluno_ano"),
    )
