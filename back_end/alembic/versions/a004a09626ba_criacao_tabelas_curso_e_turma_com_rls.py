"""Criacao tabelas Curso e Turma com RLS

Revision ID: a004a09626ba
Revises: 8da394d41364
Create Date: 2026-07-26 20:03:34.190311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# Importar o dialeto PostgreSQL para suportar UUID nativo
from sqlalchemy.dialects import postgresql 


# revision identifiers, used by Alembic.
revision: str = 'a004a09626ba'
down_revision: Union[str, Sequence[str], None] = '8da394d41364'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. CRIAÇÃO DAS TABELAS
    # ---------------------------------------------------------
    
    # Criar Tabela Curso
    op.create_table('curso',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar Tabela Turma
    op.create_table('turma',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('curso_id', sa.UUID(), nullable=False),
        sa.Column('nome_codigo', sa.String(length=50), nullable=False),
        sa.Column('ano_letivo', sa.Integer(), nullable=False),
        sa.Column('vagas_maximas', sa.Integer(), nullable=False),
        
        sa.ForeignKeyConstraint(['curso_id'], ['curso.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # ---------------------------------------------------------
    # 2. INJEÇÃO DE SEGURANÇA MULTI-TENANT (RLS)
    # ---------------------------------------------------------
    
    op.execute("ALTER TABLE curso ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_curso ON curso
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)

    op.execute("ALTER TABLE turma ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_turma ON turma
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def downgrade() -> None:
    # ---------------------------------------------------------
    # 1. REMOÇÃO DE SEGURANÇA MULTI-TENANT (RLS)
    # ---------------------------------------------------------
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_turma ON turma;")
    op.execute("ALTER TABLE turma DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS isolamento_tenant_curso ON curso;")
    op.execute("ALTER TABLE curso DISABLE ROW LEVEL SECURITY;")

    # ---------------------------------------------------------
    # 2. REMOÇÃO DAS TABELAS
    # ---------------------------------------------------------
    op.drop_table('turma')
    op.drop_table('curso')