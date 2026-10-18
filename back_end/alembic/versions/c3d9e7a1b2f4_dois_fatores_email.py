"""dois_fatores_email

Verificação em dois passos por e-mail (auditoria de segurança, bloco 5):
Usuario.dois_fatores_ativo + tabela desafio_dois_fatores.

Revision ID: c3d9e7a1b2f4
Revises: 53fb9d9aec03
Create Date: 2026-10-18 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d9e7a1b2f4'
down_revision: Union[str, Sequence[str], None] = '53fb9d9aec03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuario', sa.Column('dois_fatores_ativo', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_table('desafio_dois_fatores',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('finalidade', sa.String(length=20), nullable=False),
    sa.Column('desafio_hash', sa.String(length=64), nullable=False),
    sa.Column('codigo_hash', sa.String(length=64), nullable=False),
    sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tentativas', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('reenvios', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('usado', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('desafio_hash')
    )
    op.create_index(op.f('ix_desafio_dois_fatores_tenant_id'), 'desafio_dois_fatores', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_desafio_dois_fatores_usuario_id'), 'desafio_dois_fatores', ['usuario_id'], unique=False)

    # Mesmo isolamento por tenant de todas as outras tabelas (o login usa
    # app_sistema, mas ligar a verificação no Perfil corre com app_tenant).
    op.execute("ALTER TABLE desafio_dois_fatores ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_desafio_dois_fatores ON desafio_dois_fatores
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_desafio_dois_fatores ON desafio_dois_fatores;")
    op.drop_index(op.f('ix_desafio_dois_fatores_usuario_id'), table_name='desafio_dois_fatores')
    op.drop_index(op.f('ix_desafio_dois_fatores_tenant_id'), table_name='desafio_dois_fatores')
    op.drop_table('desafio_dois_fatores')
    op.drop_column('usuario', 'dois_fatores_ativo')
