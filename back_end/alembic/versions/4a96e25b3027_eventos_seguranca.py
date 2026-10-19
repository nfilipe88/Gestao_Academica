"""eventos_seguranca

Registo de tentativas de acesso indevido (IP, utilizador, escola, endereço).

Revision ID: 4a96e25b3027
Revises: c3d9e7a1b2f4
Create Date: 2026-10-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4a96e25b3027'
down_revision: Union[str, Sequence[str], None] = 'c3d9e7a1b2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('evento_seguranca',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('data_evento', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('tipo', sa.String(length=40), nullable=False),
    sa.Column('gravidade', sa.String(length=10), nullable=False),
    sa.Column('ip', sa.String(length=45), nullable=False),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('tenant_id', sa.Uuid(), nullable=True),
    sa.Column('usuario_id', sa.Uuid(), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('metodo', sa.String(length=10), nullable=True),
    sa.Column('caminho', sa.String(length=500), nullable=True),
    sa.Column('detalhe', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evento_seguranca_data_evento'), 'evento_seguranca', ['data_evento'], unique=False)
    op.create_index(op.f('ix_evento_seguranca_tipo'), 'evento_seguranca', ['tipo'], unique=False)
    op.create_index(op.f('ix_evento_seguranca_ip'), 'evento_seguranca', ['ip'], unique=False)
    op.create_index(op.f('ix_evento_seguranca_tenant_id'), 'evento_seguranca', ['tenant_id'], unique=False)

    # Cada escola só vê as suas; as anónimas (tenant_id nulo) só o Super Admin (app_sistema).
    op.execute("ALTER TABLE evento_seguranca ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_evento_seguranca ON evento_seguranca
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_evento_seguranca ON evento_seguranca;")
    op.drop_index(op.f('ix_evento_seguranca_tenant_id'), table_name='evento_seguranca')
    op.drop_index(op.f('ix_evento_seguranca_ip'), table_name='evento_seguranca')
    op.drop_index(op.f('ix_evento_seguranca_tipo'), table_name='evento_seguranca')
    op.drop_index(op.f('ix_evento_seguranca_data_evento'), table_name='evento_seguranca')
    op.drop_table('evento_seguranca')
