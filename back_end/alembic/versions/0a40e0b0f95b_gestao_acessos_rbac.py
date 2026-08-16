"""gestao_acessos_rbac

Revision ID: 0a40e0b0f95b
Revises: cfe1a4e36025
Create Date: 2026-08-16 22:51:04.478017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a40e0b0f95b'
down_revision: Union[str, Sequence[str], None] = 'cfe1a4e36025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Novas tabelas com isolamento por tenant — RLS ativado igual a todas
# as outras (ver padrão em migrações anteriores).
TABELAS_RLS = ["usuario_auditoria"]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('usuario_auditoria',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('usuario_alvo_id', sa.Uuid(), nullable=False),
    sa.Column('autor_id', sa.Uuid(), nullable=True),
    sa.Column('acao', sa.String(length=30), nullable=False),
    sa.Column('perfil_anterior', sa.String(length=50), nullable=True),
    sa.Column('perfil_novo', sa.String(length=50), nullable=True),
    sa.Column('detalhe', sa.Text(), nullable=True),
    sa.Column('data_acao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['autor_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_alvo_id'], ['usuario.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # NOTA: o autogenerate também detetou "drop index
    # ix_notificacao_usuario_lida_data" — drift pré-existente, sem
    # relação com esta migração (mesma situação documentada nas
    # migrações anteriores), por isso omitido aqui de propósito.
    op.add_column('usuario', sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    for tabela in TABELAS_RLS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY isolamento_tenant_{tabela} ON {tabela}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
        """)

    # Correção de uma migração anterior (cfe1a4e36025): a policy de
    # tipo_avaliacao_config foi criada a comparar com
    # current_setting('app.tenant_id') — variável que a app nunca
    # define (session.py define 'app.current_tenant_id') — e sem o
    # segundo argumento `true`, o que faria a policy REBENTAR com erro
    # em vez de simplesmente não filtrar, assim que RLS passasse a ser
    # respeitado pela ligação à base de dados. Corrige para o nome e
    # forma corretos, iguais aos de todas as outras políticas.
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_tipo_avaliacao_config ON tipo_avaliacao_config;")
    op.execute("""
        CREATE POLICY isolamento_tenant_tipo_avaliacao_config ON tipo_avaliacao_config
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_tipo_avaliacao_config ON tipo_avaliacao_config;")
    op.execute("""
        CREATE POLICY isolamento_tenant_tipo_avaliacao_config ON tipo_avaliacao_config
        USING (tenant_id = current_setting('app.tenant_id')::uuid);
    """)

    for tabela in TABELAS_RLS:
        op.execute(f"DROP POLICY IF EXISTS isolamento_tenant_{tabela} ON {tabela};")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY;")

    op.drop_column('usuario', 'ativo')
    op.drop_table('usuario_auditoria')
