"""resultado_final_matricula

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Resultado final do ano (fecho do ano letivo) gravado na matrícula:
    # APROVADO, REPROVADO ou REPROVADO_FALTAS; nulo = ano ainda não fechado.
    op.add_column('matricula', sa.Column('resultado_final', sa.String(length=20), nullable=True))
    op.add_column('matricula', sa.Column('resultado_detalhe', sa.JSON(), nullable=True))
    op.add_column('matricula', sa.Column('resultado_em', sa.DateTime(timezone=True), nullable=True))
    # Critérios da escola: quantas disciplinas pode ter em atraso e ainda
    # transitar (0 = tem de passar a todas) e limite de faltas (% das aulas).
    op.add_column('tenant', sa.Column('max_disciplinas_reprovadas', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tenant', sa.Column('limite_faltas_percentagem', sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('tenant', 'limite_faltas_percentagem')
    op.drop_column('tenant', 'max_disciplinas_reprovadas')
    op.drop_column('matricula', 'resultado_em')
    op.drop_column('matricula', 'resultado_detalhe')
    op.drop_column('matricula', 'resultado_final')
