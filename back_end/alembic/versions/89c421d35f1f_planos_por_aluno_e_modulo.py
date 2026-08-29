"""planos_por_aluno_e_modulo

Revision ID: 89c421d35f1f
Revises: cde309e6fb09
Create Date: 2026-08-29 11:45:06.687852

Planos SaaS deixam de ter um preço mensal fixo — passam a cobrar por
aluno cadastrado na escola, mais o que os módulos incluídos custarem à
parte (ver app/database/models_billing.py e app/core/modulos.py).

Renomeia (não substitui) plano_saas.preco_mensal -> preco_por_aluno
via ALTER COLUMN, para não perder os valores já configurados em planos
existentes nem falhar com linhas já lá — o autogenerate tinha detetado
isto como "coluna nova" + "coluna removida", o que apagaria os preços
configurados. O SIGNIFICADO do número muda (era o total mensal, passa
a ser por aluno) — o Super Admin tem de rever os planos existentes
depois desta migração, os valores em si não mudam sozinhos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89c421d35f1f'
down_revision: Union[str, Sequence[str], None] = 'cde309e6fb09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('plano_saas_modulo',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('plano_id', sa.Uuid(), nullable=False),
    sa.Column('modulo', sa.String(length=80), nullable=False),
    sa.Column('preco_adicional', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['plano_id'], ['plano_saas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('plano_id', 'modulo', name='uq_plano_saas_modulo')
    )
    op.alter_column('plano_saas', 'preco_mensal', new_column_name='preco_por_aluno')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('plano_saas', 'preco_por_aluno', new_column_name='preco_mensal')
    op.drop_table('plano_saas_modulo')
