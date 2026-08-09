"""Adiciona Aluno, ResponsavelFinanceiroLegal e AlunoResponsavel

Revision ID: 89b6c92bb8ff
Revises: 890a1123688a
Create Date: 2026-08-09 22:18:55.503562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89b6c92bb8ff'
down_revision: Union[str, Sequence[str], None] = '890a1123688a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. CRIAÇÃO DAS TABELAS
    # ---------------------------------------------------------
    op.create_table('aluno',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('usuario_id', sa.UUID(), nullable=True),
        sa.Column('matricula_interna', sa.String(length=50), nullable=False),
        sa.Column('nome_completo', sa.String(length=255), nullable=False),
        sa.Column('data_nascimento', sa.Date(), nullable=False),
        sa.Column('numero_documento', sa.String(length=50), nullable=True),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'matricula_interna', name='uq_aluno_tenant_matricula')
    )

    op.create_table('responsavel_financeiro_legal',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('usuario_id', sa.UUID(), nullable=True),
        sa.Column('nome_completo', sa.String(length=255), nullable=False),
        sa.Column('numero_documento', sa.String(length=50), nullable=True),
        sa.Column('telefone_contato', sa.String(length=50), nullable=False),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('aluno_responsavel',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('aluno_id', sa.UUID(), nullable=False),
        sa.Column('responsavel_id', sa.UUID(), nullable=False),
        sa.Column('tipo_parentesco', sa.String(length=50), nullable=False),
        sa.Column('responsavel_financeiro', sa.Boolean(), nullable=False, server_default=sa.false()),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['aluno_id'], ['aluno.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['responsavel_id'], ['responsavel_financeiro_legal.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aluno_id', 'responsavel_id', name='uq_aluno_responsavel')
    )

    # ---------------------------------------------------------
    # 2. RLS (mesmo padrão de curso/turma/serie_ano)
    # ---------------------------------------------------------
    for tabela, policy in [
        ('aluno', 'isolamento_tenant_aluno'),
        ('responsavel_financeiro_legal', 'isolamento_tenant_responsavel'),
        ('aluno_responsavel', 'isolamento_tenant_aluno_responsavel'),
    ]:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY {policy} ON {tabela}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
        """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_aluno_responsavel ON aluno_responsavel;")
    op.execute("ALTER TABLE aluno_responsavel DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS isolamento_tenant_responsavel ON responsavel_financeiro_legal;")
    op.execute("ALTER TABLE responsavel_financeiro_legal DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS isolamento_tenant_aluno ON aluno;")
    op.execute("ALTER TABLE aluno DISABLE ROW LEVEL SECURITY;")

    op.drop_table('aluno_responsavel')
    op.drop_table('responsavel_financeiro_legal')
    op.drop_table('aluno')
