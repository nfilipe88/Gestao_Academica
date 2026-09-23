"""periodo_janela_e_nota_exame_nacional

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-18 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [
    ("nota_exame_nacional", "isolamento_tenant_nota_exame_nacional"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # Janela calendárica do período — distinta de aberto/data_fecho
    # (que só marcam o trancamento de lançamentos). Nullable, sem
    # backfill: zero risco para os períodos já existentes, que ficam
    # simplesmente sem faltas-por-trimestre disponíveis na Pauta até
    # o Gestor preencher via PATCH.
    op.add_column('periodo_avaliacao', sa.Column('data_inicio', sa.Date(), nullable=True))
    op.add_column('periodo_avaliacao', sa.Column('data_fim', sa.Date(), nullable=True))

    op.create_table('nota_exame_nacional',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('matricula_id', sa.Uuid(), nullable=False),
    sa.Column('disciplina_id', sa.Uuid(), nullable=False),
    sa.Column('valor_nota', sa.Numeric(4, 2), nullable=False),
    sa.Column('lancado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('data_lancamento', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['lancado_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('matricula_id', 'disciplina_id', name='uq_nen_matricula_disciplina')
    )
    op.create_index(op.f('ix_nota_exame_nacional_tenant_id'), 'nota_exame_nacional', ['tenant_id'], unique=False)

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

    op.drop_index(op.f('ix_nota_exame_nacional_tenant_id'), table_name='nota_exame_nacional')
    op.drop_table('nota_exame_nacional')

    op.drop_column('periodo_avaliacao', 'data_fim')
    op.drop_column('periodo_avaliacao', 'data_inicio')
