"""perfil_nome

Nome mostrado de cada perfil, editável pelo Super Admin (o código fica igual).

Revision ID: 1ad4a0c93e53
Revises: 4a96e25b3027
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1ad4a0c93e53'
down_revision: Union[str, Sequence[str], None] = '4a96e25b3027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PERFIS = [
    ("SUPER_ADMIN", "Super Admin", 1),
    ("GESTOR", "Gestor", 2),
    ("SECRETARIA", "Secretaria", 3),
    ("PROFESSOR", "Professor", 4),
    ("ALUNO", "Aluno", 5),
    ("RESPONSAVEL", "Responsável", 6),
]


def upgrade() -> None:
    tabela = op.create_table('perfil_nome',
    sa.Column('codigo', sa.String(length=30), nullable=False),
    sa.Column('nome', sa.String(length=60), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('codigo')
    )
    op.bulk_insert(tabela, [{"codigo": c, "nome": n, "ordem": o} for c, n, o in _PERFIS])


def downgrade() -> None:
    op.drop_table('perfil_nome')
