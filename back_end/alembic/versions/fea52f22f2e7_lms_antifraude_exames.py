"""lms_antifraude_exames

Revision ID: fea52f22f2e7
Revises: d0e1f2a3b4c5
Create Date: 2026-09-30 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fea52f22f2e7'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Condição de acesso ao exame (LMSExame) — exigir câmara/microfone
    # ligados, verificado só no browser do aluno.
    op.add_column('lms_exame', sa.Column('exigir_camera', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('lms_exame', sa.Column('exigir_microfone', sa.Boolean(), server_default='false', nullable=False))

    # Anti-fraude da tentativa (LMSTentativaExame) — nenhuma tentativa
    # já existente estava anulada nem tinha amostras de foco, por isso
    # um valor escalar chega para todas as linhas atuais.
    op.add_column('lms_tentativa_exame', sa.Column('anulada', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('lms_tentativa_exame', sa.Column('anulada_motivo', sa.String(length=255), nullable=True))
    op.add_column('lms_tentativa_exame', sa.Column('anulada_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lms_tentativa_exame', sa.Column('amostras_foco_total', sa.Integer(), server_default='0', nullable=False))
    op.add_column('lms_tentativa_exame', sa.Column('amostras_foco_positivas', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lms_tentativa_exame', 'amostras_foco_positivas')
    op.drop_column('lms_tentativa_exame', 'amostras_foco_total')
    op.drop_column('lms_tentativa_exame', 'anulada_em')
    op.drop_column('lms_tentativa_exame', 'anulada_motivo')
    op.drop_column('lms_tentativa_exame', 'anulada')
    op.drop_column('lms_exame', 'exigir_microfone')
    op.drop_column('lms_exame', 'exigir_camera')
