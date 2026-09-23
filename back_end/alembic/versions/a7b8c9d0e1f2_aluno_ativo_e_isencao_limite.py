"""aluno_ativo_e_isencao_limite

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-23 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Desativar em vez de eliminar (retenção legal de 15 anos) — todos os
    # alunos existentes ficam ativos, nada muda para quem já usa a app.
    op.add_column('aluno', sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    # Isenção do limite de alunos do plano, concedida pelo Super Admin.
    op.add_column('tenant', sa.Column('isento_limite_alunos', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenant', 'isento_limite_alunos')
    op.drop_column('aluno', 'ativo')
