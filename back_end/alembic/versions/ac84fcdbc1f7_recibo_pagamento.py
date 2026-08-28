"""recibo_pagamento

Revision ID: ac84fcdbc1f7
Revises: 9fa20e69c1f6
Create Date: 2026-08-28 13:25:34.332963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac84fcdbc1f7'
down_revision: Union[str, Sequence[str], None] = '9fa20e69c1f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [
    ("contador_recibo", "isolamento_tenant_contador_recibo"),
    ("recibo", "isolamento_tenant_recibo"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (ver a mesma nota nas migrações anteriores).
    op.create_table('contador_recibo',
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('ano', sa.Integer(), nullable=False),
    sa.Column('proximo_numero', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tenant_id', 'ano')
    )
    op.create_table('recibo',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('fatura_id', sa.Uuid(), nullable=False),
    sa.Column('numero_sequencial', sa.Integer(), nullable=False),
    sa.Column('ano', sa.Integer(), nullable=False),
    sa.Column('data_emissao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('valor', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('moeda', sa.String(length=3), nullable=False),
    sa.Column('forma_pagamento', sa.String(length=30), nullable=False),
    sa.Column('nome_pagador', sa.String(length=255), nullable=False),
    sa.Column('numero_documento_pagador', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['fatura_id'], ['fatura_mensalidade.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fatura_id', name='uq_recibo_fatura'),
    sa.UniqueConstraint('tenant_id', 'ano', 'numero_sequencial', name='uq_recibo_tenant_ano_numero')
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

    op.drop_table('recibo')
    op.drop_table('contador_recibo')
