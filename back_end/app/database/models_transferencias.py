"""
Pedido de transferência de um Aluno desta instituição (tenant_id, a
"origem") para outra instituição desta mesma plataforma (tenant_destino_id).

Migração real: aprovar um pedido cria um NOVO Aluno (+ Responsáveis)
no tenant de destino com os dados de identidade copiados, e marca a
Matricula de origem como TRANSFERIDO. Histórico académico/financeiro
(notas, frequência, faturas) NÃO é migrado — fica na escola de origem
e pode ser pedido como Histórico Escolar via Solicitações de Documentos.

Cobre dois cenários, distinguidos pelo status da matrícula de origem
no momento do pedido (ver cruds/transferencias.py::criar_solicitacao):
- ATIVO: transferência "a quente" — o aluno ainda frequenta a escola
  de origem. Ao pedir, a matrícula passa a EM_TRANSFERENCIA (suspensa
  enquanto a escola de destino decide — ver ESTADOS_VALIDOS em
  cruds/matriculas.py); aprovar conclui para TRANSFERIDO, rejeitar
  devolve a ATIVO.
- CICLO_CONCLUIDO ("Fim de Ciclo" — ver cruds/matriculas.py): o aluno
  já tinha saído desta escola (concluiu o que ela oferece, ou foi para
  fora da plataforma) e só agora aparece a querer continuar noutra
  escola DESTA plataforma — "Reingresso cross-escola". A matrícula de
  origem fica como estava (CICLO_CONCLUIDO) em qualquer desfecho: o
  Fim de Ciclo continua a ser um facto histórico verdadeiro, só porque
  o aluno reapareceu meses depois não deixou de ter acontecido.

Decisão direta entre instituições: quem aprova/rejeita é o Gestor/
Secretaria da instituição de DESTINO (não o Super Admin — ver
histórico deste ficheiro para o desenho anterior, que passava por
aprovação centralizada e foi removido por ser burocrático sem
necessidade). O Super Admin mantém só uma listagem de leitura,
cross-tenant, para efeitos de auditoria (GET /transferencias) — não
decide.
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

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
