"""pagamento_reportado_fatura

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-19 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Auto-relato do Responsável ("já efetuei a transferência") — aditivo,
    # não é um novo status_pagamento (ver docstring de FaturaMensalidade);
    # nullable, sem backfill: faturas existentes ficam simplesmente sem
    # relato, como se ninguém tivesse reportado nada ainda.
    op.add_column('fatura_mensalidade', sa.Column('pagamento_reportado_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('fatura_mensalidade', sa.Column('pagamento_reportado_referencia', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('fatura_mensalidade', 'pagamento_reportado_referencia')
    op.drop_column('fatura_mensalidade', 'pagamento_reportado_em')
