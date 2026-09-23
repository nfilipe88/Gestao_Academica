"""aceitacao_termos_tenant

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-23 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Prova de que a escola aceitou a Política de Privacidade/Termos no
    # registo (e qual a versão) — nullable: escolas criadas antes disto, ou
    # pelo Super Admin, ficam sem registo em vez de um valor inventado.
    op.add_column('tenant', sa.Column('termos_aceites_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenant', sa.Column('termos_versao', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenant', 'termos_versao')
    op.drop_column('tenant', 'termos_aceites_em')
