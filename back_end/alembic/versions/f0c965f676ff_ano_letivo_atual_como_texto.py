"""ano_letivo_atual_como_texto

Revision ID: f0c965f676ff
Revises: f76cb7ec66e8
Create Date: 2026-09-06 15:22:33.485217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0c965f676ff'
down_revision: Union[str, Sequence[str], None] = 'f76cb7ec66e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pedido do utilizador logo a seguir a f76cb7ec66e8: o Ano Letivo
    # (Tenant.ano_letivo_atual) passa a ser a junção "YYYY/YYYY" dos
    # anos de início e fim (ex.: "2026/2027"), não só o ano de início
    # como inteiro — ver comentário em app/database/models.py. Postgres
    # não converte INTEGER → VARCHAR automaticamente num ALTER COLUMN,
    # por isso o USING explícito (::text); os valores já gravados como
    # inteiro solto (ex.: "2026") ficam assim até o Gestor voltar a
    # guardar a Configuração.
    op.alter_column('tenant', 'ano_letivo_atual',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=9),
               existing_nullable=True,
               postgresql_using='ano_letivo_atual::text')


def downgrade() -> None:
    """Downgrade schema."""
    # NOTA: falha se algum valor já gravado estiver no formato
    # "YYYY/YYYY" (não converte para inteiro) — esperado, é um downgrade
    # de uma mudança de formato, não tem forma sem perda de o fazer.
    op.alter_column('tenant', 'ano_letivo_atual',
               existing_type=sa.String(length=9),
               type_=sa.INTEGER(),
               existing_nullable=True,
               postgresql_using='ano_letivo_atual::integer')
