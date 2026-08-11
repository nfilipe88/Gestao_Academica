"""Adiciona Disciplina e Grade Curricular

Revision ID: 2107cb3896fc
Revises: 49f8a4bef613
Create Date: 2026-08-11 23:58:04.280924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2107cb3896fc'
down_revision: Union[str, Sequence[str], None] = '49f8a4bef613'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('disciplina',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('carga_horaria_total', sa.Integer(), nullable=True),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.execute("ALTER TABLE disciplina ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_disciplina ON disciplina
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)

    op.create_table('grade_curricular',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('serie_ano_id', sa.UUID(), nullable=False),
        sa.Column('disciplina_id', sa.UUID(), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['serie_ano_id'], ['serie_ano.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serie_ano_id', 'disciplina_id', name='uq_grade_serie_disciplina')
    )
    op.execute("ALTER TABLE grade_curricular ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_grade_curricular ON grade_curricular
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_grade_curricular ON grade_curricular;")
    op.execute("ALTER TABLE grade_curricular DISABLE ROW LEVEL SECURITY;")
    op.drop_table('grade_curricular')

    op.execute("DROP POLICY IF EXISTS isolamento_tenant_disciplina ON disciplina;")
    op.execute("ALTER TABLE disciplina DISABLE ROW LEVEL SECURITY;")
    op.drop_table('disciplina')
