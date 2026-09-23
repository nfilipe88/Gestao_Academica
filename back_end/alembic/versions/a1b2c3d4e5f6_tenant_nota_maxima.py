"""tenant_nota_maxima

Revision ID: a1b2c3d4e5f6
Revises: f9c7d1e1d3a5
Create Date: 2026-09-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f9c7d1e1d3a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOT NULL com server_default='10' — preserva exatamente o
    # comportamento fixo anterior (NOTA_MAXIMA=10 em cruds/diario.py)
    # para todas as escolas já existentes; passa a ser editável (e
    # obrigatório no formulário) em Configurações.
    op.add_column('tenant', sa.Column('nota_maxima', sa.Numeric(precision=4, scale=2), server_default=sa.text('10'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenant', 'nota_maxima')
