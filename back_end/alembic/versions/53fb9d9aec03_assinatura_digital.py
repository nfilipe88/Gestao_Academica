"""assinatura_digital

Revision ID: 53fb9d9aec03
Revises: fea52f22f2e7
Create Date: 2026-09-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53fb9d9aec03'
down_revision: Union[str, Sequence[str], None] = 'fea52f22f2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mesma convenção RLS do resto do schema.
TABELAS_RLS = [
    ("assinatura_usuario", "isolamento_tenant_assinatura_usuario"),
    ("assinante_documento", "isolamento_tenant_assinante_documento"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # Assinatura pessoal por utilizador (versionada, mesmo padrão de FotoPerfilAluno).
    op.create_table('assinatura_usuario',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('chave_storage', sa.String(length=500), nullable=False),
    sa.Column('ativa', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('enviada_em', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assinatura_usuario_tenant_id'), 'assinatura_usuario', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_assinatura_usuario_usuario_id'), 'assinatura_usuario', ['usuario_id'], unique=False)

    # Quem assina cada TIPO de documento formal — decisão administrativa da
    # escola (ver app/core/assinaturas.py); a imagem em si vem sempre da
    # assinatura pessoal (assinatura_usuario) do usuario_id designado.
    op.create_table('assinante_documento',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('tipo_documento', sa.String(length=30), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('cargo', sa.String(length=255), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'tipo_documento', 'usuario_id', name='uq_assinante_documento_tenant_tipo_usuario')
    )
    op.create_index(op.f('ix_assinante_documento_tenant_id'), 'assinante_documento', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_assinante_documento_usuario_id'), 'assinante_documento', ['usuario_id'], unique=False)

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

    op.drop_index(op.f('ix_assinante_documento_usuario_id'), table_name='assinante_documento')
    op.drop_index(op.f('ix_assinante_documento_tenant_id'), table_name='assinante_documento')
    op.drop_table('assinante_documento')

    op.drop_index(op.f('ix_assinatura_usuario_usuario_id'), table_name='assinatura_usuario')
    op.drop_index(op.f('ix_assinatura_usuario_tenant_id'), table_name='assinatura_usuario')
    op.drop_table('assinatura_usuario')
