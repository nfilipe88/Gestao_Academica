"""password_reset_token

Revision ID: c5114fc15f70
Revises: 0a40e0b0f95b
Create Date: 2026-08-17 01:46:40.930346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5114fc15f70'
down_revision: Union[str, Sequence[str], None] = '0a40e0b0f95b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Nova tabela com isolamento por tenant — RLS ativado igual a todas as
# outras (ver padrão em migrações anteriores). Na prática só é escrita/
# lida pelo role app_sistema (fluxo de recuperação de senha é
# pré-autenticado, ver cruds/auth.py), mas ganha a policy por
# consistência e defesa em profundidade, como todas as outras tabelas.
TABELAS_RLS = ["password_reset_token"]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('password_reset_token',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usado', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )

    for tabela in TABELAS_RLS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY isolamento_tenant_{tabela} ON {tabela}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
        """)


def downgrade() -> None:
    """Downgrade schema."""
    for tabela in TABELAS_RLS:
        op.execute(f"DROP POLICY IF EXISTS isolamento_tenant_{tabela} ON {tabela};")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY;")

    op.drop_table('password_reset_token')
