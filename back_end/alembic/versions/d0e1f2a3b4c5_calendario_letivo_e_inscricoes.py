"""calendario_letivo_e_inscricoes

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-24 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [("calendario_letivo", "isolamento_tenant_calendario_letivo")]


def upgrade() -> None:
    # Abrir/encerrar matrículas e rematrículas de autoatendimento (candidatura
    # pública e pedido de rematrícula no Portal). Existentes ficam abertas.
    op.add_column('tenant', sa.Column('matriculas_abertas', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('tenant', sa.Column('rematriculas_abertas', sa.Boolean(), nullable=False, server_default=sa.text('true')))

    op.create_table('calendario_letivo',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('ano_letivo', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=30), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_fim', sa.Date(), nullable=False),
        sa.Column('observacoes', sa.String(length=500), nullable=True),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_calendario_letivo_tenant_ano', 'calendario_letivo', ['tenant_id', 'ano_letivo'])

    for tabela, policy in TABELAS_RLS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY {policy} ON {tabela}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
        """)


def downgrade() -> None:
    for tabela, policy in reversed(TABELAS_RLS):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {tabela};")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY;")
    op.drop_index('ix_calendario_letivo_tenant_ano', table_name='calendario_letivo')
    op.drop_table('calendario_letivo')
    op.drop_column('tenant', 'rematriculas_abertas')
    op.drop_column('tenant', 'matriculas_abertas')
