"""foto_perfil_aluno

Revision ID: f1e2a3b4c5d6
Revises: d3f1a9c6b204
Create Date: 2026-08-30 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1e2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd3f1a9c6b204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mesma convenção RLS do resto do schema.
TABELAS_RLS = [("foto_perfil_aluno", "isolamento_tenant_foto_perfil_aluno")]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('foto_perfil_aluno',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('aluno_id', sa.Uuid(), nullable=False),
    sa.Column('ano_letivo', sa.Integer(), nullable=False),
    sa.Column('nome_original', sa.String(length=255), nullable=False),
    sa.Column('chave_storage', sa.String(length=500), nullable=False),
    sa.Column('ativa', sa.Boolean(), nullable=False),
    sa.Column('enviada_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('data_envio', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['aluno_id'], ['aluno.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['enviada_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_foto_perfil_aluno_aluno_id'), 'foto_perfil_aluno', ['aluno_id'], unique=False)
    op.create_index(op.f('ix_foto_perfil_aluno_tenant_id'), 'foto_perfil_aluno', ['tenant_id'], unique=False)

    for tabela, policy in TABELAS_RLS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY {policy} ON {tabela}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
        """)


def downgrade() -> None:
    """Downgrade schema."""
    for tabela, policy in reversed(TABELAS_RLS):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {tabela};")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY;")

    op.drop_index(op.f('ix_foto_perfil_aluno_tenant_id'), table_name='foto_perfil_aluno')
    op.drop_index(op.f('ix_foto_perfil_aluno_aluno_id'), table_name='foto_perfil_aluno')
    op.drop_table('foto_perfil_aluno')
