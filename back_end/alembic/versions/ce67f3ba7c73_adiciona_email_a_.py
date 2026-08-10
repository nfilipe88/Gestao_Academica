"""Adiciona email a ResponsavelFinanceiroLegal

Revision ID: ce67f3ba7c73
Revises: 89b6c92bb8ff
Create Date: 2026-08-10 23:48:03.660014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce67f3ba7c73'
down_revision: Union[str, Sequence[str], None] = '89b6c92bb8ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('responsavel_financeiro_legal', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('responsavel_financeiro_legal', 'email')
