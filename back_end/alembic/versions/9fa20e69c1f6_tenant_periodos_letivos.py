"""tenant_periodos_letivos

Revision ID: 9fa20e69c1f6
Revises: 27164a3610e5
Create Date: 2026-08-19 07:28:47.795372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fa20e69c1f6'
down_revision: Union[str, Sequence[str], None] = '27164a3610e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (ver a mesma nota nas migrações anteriores).
    op.add_column('tenant', sa.Column('periodo_manha_inicio', sa.Time(), nullable=True))
    op.add_column('tenant', sa.Column('periodo_manha_fim', sa.Time(), nullable=True))
    op.add_column('tenant', sa.Column('periodo_tarde_inicio', sa.Time(), nullable=True))
    op.add_column('tenant', sa.Column('periodo_tarde_fim', sa.Time(), nullable=True))
    op.add_column('tenant', sa.Column('periodo_pos_laboral_inicio', sa.Time(), nullable=True))
    op.add_column('tenant', sa.Column('periodo_pos_laboral_fim', sa.Time(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenant', 'periodo_pos_laboral_fim')
    op.drop_column('tenant', 'periodo_pos_laboral_inicio')
    op.drop_column('tenant', 'periodo_tarde_fim')
    op.drop_column('tenant', 'periodo_tarde_inicio')
    op.drop_column('tenant', 'periodo_manha_fim')
    op.drop_column('tenant', 'periodo_manha_inicio')
