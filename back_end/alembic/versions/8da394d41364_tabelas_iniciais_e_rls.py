"""Tabelas iniciais e RLS

Revision ID: 8da394d41364
Revises: 
Create Date: 2026-07-20 23:30:15.181958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8da394d41364'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # ---------------------------------------------------------
    # 1. CRIAÇÃO DAS TABELAS (estava em falta nesta migration)
    # ---------------------------------------------------------
    op.create_table('tenant',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('nome_fantasia', sa.String(length=255), nullable=False),
        sa.Column('razao_social', sa.String(length=255), nullable=True),
        sa.Column('nif', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ATIVO'),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nif')
    )

    op.create_table('usuario',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('nome_completo', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('senha_hash', sa.String(length=255), nullable=False),
        sa.Column('perfil_acesso', sa.String(length=50), nullable=False),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # ---------------------------------------------------------
    # 2. Ativar o RLS na tabela de utilizadores
    # ---------------------------------------------------------
    op.execute("ALTER TABLE usuario ENABLE ROW LEVEL SECURITY;")
    
    # 3. Criar a política de isolamento forçando o Postgres a respeitar a variável de sessão
    op.execute("""
        CREATE POLICY isolamento_tenant_usuario ON usuario
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Remover a política de isolamento
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_usuario ON usuario;")

    # 2. Desativar o RLS na tabela de utilizadores
    op.execute("ALTER TABLE usuario DISABLE ROW LEVEL SECURITY;")

    # 3. Remover as tabelas (usuario antes de tenant, por causa da FK)
    op.drop_table('usuario')
    op.drop_table('tenant')