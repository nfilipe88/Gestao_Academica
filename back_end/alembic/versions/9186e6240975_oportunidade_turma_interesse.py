"""oportunidade turma interesse

Revision ID: 9186e6240975
Revises: c5114fc15f70
Create Date: 2026-08-17 23:17:19.280651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9186e6240975'
down_revision: Union[str, Sequence[str], None] = 'c5114fc15f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (modelo atual não define esse índice), por isso foi deliberadamente
    # excluído desta migração para a manter focada só na Turma pretendida.
    op.add_column('oportunidade_crm', sa.Column('turma_interesse_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(None, 'oportunidade_crm', 'turma', ['turma_interesse_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'oportunidade_crm', type_='foreignkey')
    op.drop_column('oportunidade_crm', 'turma_interesse_id')
