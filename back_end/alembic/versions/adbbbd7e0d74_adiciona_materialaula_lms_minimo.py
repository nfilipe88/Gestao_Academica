"""Adiciona MaterialAula (LMS minimo)

Revision ID: adbbbd7e0d74
Revises: 516afb775cd8
Create Date: 2026-08-15 23:40:53.970759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adbbbd7e0d74'
down_revision: Union[str, Sequence[str], None] = '516afb775cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nota: o autogenerate voltou a detetar a remoção do índice
# ix_notificacao_usuario_lida_data em "notificacao" — mesmo drift não
# relacionado já visto nas duas migrações anteriores; omitido de propósito.

TABELAS_RLS = [
    ("material_aula", "isolamento_tenant_material_aula"),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('material_aula',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('turma_id', sa.Uuid(), nullable=False),
    sa.Column('disciplina_id', sa.Uuid(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('corpo', sa.Text(), nullable=False),
    sa.Column('objetivo_aprendizagem_id', sa.Uuid(), nullable=True),
    sa.Column('publicado', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('criado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('data_atualizacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['objetivo_aprendizagem_id'], ['objetivo_aprendizagem.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['turma_id'], ['turma.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
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

    op.drop_table('material_aula')
