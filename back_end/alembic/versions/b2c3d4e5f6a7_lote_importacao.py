"""lote_importacao

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-17 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mesmo padrão de RLS de sempre — lote_importacao (pai) + lote_importacao_aluno (filho).
TABELAS_RLS = [
    ("lote_importacao", "lote_importacao_tenant_isolation"),
    ("lote_importacao_aluno", "lote_importacao_aluno_tenant_isolation"),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('lote_importacao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('criado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('nome_ficheiro_original', sa.String(length=255), nullable=False),
    sa.Column('chave_storage_ficheiro', sa.String(length=500), nullable=False),
    sa.Column('turma_id', sa.Uuid(), nullable=False),
    sa.Column('disciplina_id', sa.Uuid(), nullable=False),
    sa.Column('ano_letivo', sa.Integer(), nullable=False),
    sa.Column('total_alunos_criados', sa.Integer(), nullable=False),
    sa.Column('total_alunos_reaproveitados', sa.Integer(), nullable=False),
    sa.Column('total_notas_lancadas', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('data_desfeito', sa.DateTime(timezone=True), nullable=True),
    sa.Column('desfeito_por_usuario_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['desfeito_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['turma_id'], ['turma.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lote_importacao_tenant_id'), 'lote_importacao', ['tenant_id'], unique=False)

    op.create_table('lote_importacao_aluno',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('lote_importacao_id', sa.Uuid(), nullable=False),
    sa.Column('aluno_id', sa.Uuid(), nullable=False),
    sa.Column('matricula_id', sa.Uuid(), nullable=False),
    sa.Column('aluno_pre_existente', sa.Boolean(), nullable=False),
    sa.Column('data_nascimento_estimada', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['aluno_id'], ['aluno.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['lote_importacao_id'], ['lote_importacao.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('lote_importacao_id', 'aluno_id', name='uq_lote_aluno')
    )
    op.create_index(op.f('ix_lote_importacao_aluno_tenant_id'), 'lote_importacao_aluno', ['tenant_id'], unique=False)

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

    op.drop_index(op.f('ix_lote_importacao_aluno_tenant_id'), table_name='lote_importacao_aluno')
    op.drop_table('lote_importacao_aluno')
    op.drop_index(op.f('ix_lote_importacao_tenant_id'), table_name='lote_importacao')
    op.drop_table('lote_importacao')
