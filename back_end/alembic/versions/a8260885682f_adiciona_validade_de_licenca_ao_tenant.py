"""adiciona validade de licenca ao tenant

Revision ID: a8260885682f
Revises: 0b10ab0d7537
Create Date: 2026-08-15 12:44:41.900020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8260885682f'
down_revision: Union[str, Sequence[str], None] = '0b10ab0d7537'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # (o "drop_index ix_notificacao_usuario_lida_data" que o autogenerate
    # detetou aqui é um falso positivo, tal como nas migrações
    # anteriores — esse índice continua a ser necessário, por isso não
    # está incluído.)
    op.add_column('tenant', sa.Column('data_validade_licenca', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenant', 'data_validade_licenca')
