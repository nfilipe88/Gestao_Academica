"""Adiciona Comunicado

Revision ID: 49f8a4bef613
Revises: dbfc739c3b61
Create Date: 2026-08-11 23:44:45.367376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49f8a4bef613'
down_revision: Union[str, Sequence[str], None] = 'dbfc739c3b61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('comunicado',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('autor_id', sa.UUID(), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('corpo', sa.Text(), nullable=False),
        sa.Column('destinatario_tipo', sa.String(length=20), nullable=False),
        sa.Column('destinatario_turma_id', sa.UUID(), nullable=True),
        sa.Column('destinatario_aluno_id', sa.UUID(), nullable=True),
        sa.Column('total_destinatarios', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data_envio', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['autor_id'], ['usuario.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['destinatario_turma_id'], ['turma.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['destinatario_aluno_id'], ['aluno.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("ALTER TABLE comunicado ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_comunicado ON comunicado
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_comunicado ON comunicado;")
    op.execute("ALTER TABLE comunicado DISABLE ROW LEVEL SECURITY;")
    op.drop_table('comunicado')
