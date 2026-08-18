"""saas billing planos assinaturas

Revision ID: e6be87fed8e2
Revises: acc8c8ec166f
Create Date: 2026-08-18 23:10:18.196466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6be87fed8e2'
down_revision: Union[str, Sequence[str], None] = 'acc8c8ec166f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# plano_saas fica de fora — é catálogo global, sem tenant_id (só o
# Super Admin gere, via sessão bypassrls). assinatura_tenant tem RLS
# por pertencer claramente a um tenant, mesmo hoje só sendo tocada
# pela mesma sessão de sistema.
TABELAS_RLS = [("assinatura_tenant", "isolamento_tenant_assinatura_tenant")]


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (ver a mesma nota nas migrações anteriores).
    op.create_table('plano_saas',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('nome', sa.String(length=50), nullable=False),
    sa.Column('preco_mensal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('limite_alunos', sa.Integer(), nullable=True),
    sa.Column('descricao', sa.String(length=500), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nome')
    )
    op.create_table('assinatura_tenant',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('plano_id', sa.Uuid(), nullable=False),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('proxima_cobranca', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('data_atualizacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['plano_id'], ['plano_saas.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', name='uq_assinatura_tenant_tenant')
    )

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

    op.drop_table('assinatura_tenant')
    op.drop_table('plano_saas')
