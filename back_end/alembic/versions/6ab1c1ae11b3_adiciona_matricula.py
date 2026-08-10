"""Adiciona Matricula

Revision ID: 6ab1c1ae11b3
Revises: ce67f3ba7c73
Create Date: 2026-08-11 00:05:29.587060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ab1c1ae11b3'
down_revision: Union[str, Sequence[str], None] = 'ce67f3ba7c73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('matricula',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('aluno_id', sa.UUID(), nullable=False),
        sa.Column('turma_id', sa.UUID(), nullable=False),
        sa.Column('ano_letivo', sa.Integer(), nullable=False),
        sa.Column('status_matricula', sa.String(length=20), nullable=False, server_default='ATIVO'),
        sa.Column('data_matricula', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['aluno_id'], ['aluno.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['turma_id'], ['turma.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aluno_id', 'turma_id', 'ano_letivo', name='uq_matricula_aluno_turma_ano')
    )

    op.execute("ALTER TABLE matricula ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_matricula ON matricula
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_matricula ON matricula;")
    op.execute("ALTER TABLE matricula DISABLE ROW LEVEL SECURITY;")
    op.drop_table('matricula')
