"""perfil_suporte

Perfil SUPORTE (equipa da plataforma): nome mostrado por omissão.

Revision ID: 8481eed915e9
Revises: 1ad4a0c93e53
Create Date: 2026-10-19 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '8481eed915e9'
down_revision: Union[str, Sequence[str], None] = '1ad4a0c93e53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("INSERT INTO perfil_nome (codigo, nome, ordem) VALUES ('SUPORTE', 'Suporte', 7) ON CONFLICT (codigo) DO NOTHING")


def downgrade() -> None:
    op.execute("DELETE FROM perfil_nome WHERE codigo = 'SUPORTE'")
