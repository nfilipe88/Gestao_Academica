"""trilha recuperacao

Revision ID: 674b992b82ff
Revises: 9186e6240975
Create Date: 2026-08-18 08:29:36.000352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '674b992b82ff'
down_revision: Union[str, Sequence[str], None] = '9186e6240975'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [("trilha_recuperacao", "isolamento_tenant_trilha_recuperacao")]


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança,
    # por isso excluído desta migração (ver mesma nota em
    # 9186e6240975_oportunidade_turma_interesse.py).
    op.create_table('trilha_recuperacao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('aluno_id', sa.Uuid(), nullable=False),
    sa.Column('matricula_id', sa.Uuid(), nullable=False),
    sa.Column('gerada_por', sa.Uuid(), nullable=True),
    sa.Column('pontuacao_risco_momento', sa.Integer(), nullable=False),
    sa.Column('nivel_risco_momento', sa.String(length=10), nullable=False),
    sa.Column('conteudo', sa.Text(), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['aluno_id'], ['aluno.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['gerada_por'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
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

    op.drop_table('trilha_recuperacao')
