"""storage_fase4

Revision ID: 8791f34dff78
Revises: ac84fcdbc1f7
Create Date: 2026-08-28 14:37:29.167784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8791f34dff78'
down_revision: Union[str, Sequence[str], None] = 'ac84fcdbc1f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [
    ("anexo_comunicacao", "isolamento_tenant_anexo_comunicacao"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (ver a mesma nota nas migrações anteriores).
    op.create_table('anexo_comunicacao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('comunicado_id', sa.Uuid(), nullable=False),
    sa.Column('chave_storage', sa.String(length=500), nullable=False),
    sa.Column('nome_original', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('tamanho_bytes', sa.BigInteger(), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['comunicado_id'], ['comunicado.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('tenant', sa.Column('logotipo_chave', sa.String(length=500), nullable=True))

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

    op.drop_column('tenant', 'logotipo_chave')
    op.drop_table('anexo_comunicacao')
