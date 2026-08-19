"""plano_dias_periodo_teste

Revision ID: 9bd4aa4a4845
Revises: 584537bbba2e
Create Date: 2026-08-19 01:14:48.463391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bd4aa4a4845'
down_revision: Union[str, Sequence[str], None] = '584537bbba2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (ver a mesma nota nas migrações anteriores).
    op.add_column('plano_saas', sa.Column(
        'dias_periodo_teste', sa.Integer(), nullable=False, server_default='0'
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('plano_saas', 'dias_periodo_teste')
