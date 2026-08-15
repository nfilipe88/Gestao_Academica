"""Adiciona ObjetivoAprendizagem e Avaliacao.objetivo_aprendizagem_id

Revision ID: 516afb775cd8
Revises: 7dc8e491b65e
Create Date: 2026-08-15 21:23:40.934266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '516afb775cd8'
down_revision: Union[str, Sequence[str], None] = '7dc8e491b65e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nota: o autogenerate voltou a detetar a remoção do índice
# ix_notificacao_usuario_lida_data em "notificacao" — o mesmo drift não
# relacionado já visto na migração anterior (7dc8e491b65e); omitido de
# propósito outra vez.

TABELAS_RLS = [
    ("objetivo_aprendizagem", "isolamento_tenant_objetivo_aprendizagem"),
]

_FK_AVALIACAO_OBJETIVO = "fk_avaliacao_objetivo_aprendizagem_id"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('objetivo_aprendizagem',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('disciplina_id', sa.Uuid(), nullable=False),
    sa.Column('nome', sa.String(length=150), nullable=False),
    sa.Column('descricao', sa.String(length=500), nullable=True),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('disciplina_id', 'nome', name='uq_objetivo_disciplina_nome')
    )
    op.add_column('avaliacao', sa.Column('objetivo_aprendizagem_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(_FK_AVALIACAO_OBJETIVO, 'avaliacao', 'objetivo_aprendizagem', ['objetivo_aprendizagem_id'], ['id'], ondelete='SET NULL')

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

    op.drop_constraint(_FK_AVALIACAO_OBJETIVO, 'avaliacao', type_='foreignkey')
    op.drop_column('avaliacao', 'objetivo_aprendizagem_id')
    op.drop_table('objetivo_aprendizagem')
