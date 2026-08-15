"""
Pedido de transferência de um Aluno desta instituição (tenant_id, a
"origem") para outra instituição desta mesma plataforma (tenant_destino_id).

Migração real: aprovar um pedido cria um NOVO Aluno (+ Responsáveis)
no tenant de destino com os dados de identidade copiados, e marca a
Matricula de origem como TRANSFERIDO. Histórico académico/financeiro
(notas, frequência, faturas) NÃO é migrado — fica na escola de origem
e pode ser pedido como Histórico Escolar via Solicitações de Documentos.

Só o Super Admin pode aprovar/rejeitar (é a única entidade com alcance
legítimo sobre duas instituições ao mesmo tempo).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class SolicitacaoTransferencia(Base):
    __tablename__ = "solicitacao_transferencia"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # "Dono" do pedido para efeitos de RLS — a instituição de origem.
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)

    aluno_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    solicitado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    tenant_destino_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    nif_destino: Mapped[str] = mapped_column(String(50), nullable=False)

    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # PENDENTE, REJEITADA, CONCLUIDA
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE")
    observacoes_decisao: Mapped[str | None] = mapped_column(Text, nullable=True)
    # id do novo Aluno criado no tenant de destino, uma vez concluída a
    # migração — sem FK (aponta para uma linha noutro tenant, na mesma
    # tabela física; uma FK aqui sugeriria uma relação dentro do mesmo
    # espaço lógico, o que não é o caso).
    aluno_novo_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    data_solicitacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_decisao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
