"""lms_correcao_manual

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-18 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default escalar chega para as duas colunas — ao contrário
    # de grupo_id (que precisava de um UUID DIFERENTE por linha), aqui
    # o MESMO valor está correto para todas as linhas já existentes:
    # toda a correção, até agora, foi sempre 100% automática e
    # finalizada, e nenhuma tinha correções manuais registadas.
    op.add_column('lms_tentativa_exame', sa.Column('corrigida_finalizada', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('lms_tentativa_exame', sa.Column('correcoes_manuais', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('lms_tentativa_exame', sa.Column('corrigido_por_usuario_id', sa.Uuid(), nullable=True))
    op.add_column('lms_tentativa_exame', sa.Column('corrigido_em', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key(
        'fk_lms_tentativa_exame_corrigido_por_usuario_id', 'lms_tentativa_exame', 'usuario',
        ['corrigido_por_usuario_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_lms_tentativa_exame_corrigido_por_usuario_id', 'lms_tentativa_exame', type_='foreignkey')
    op.drop_column('lms_tentativa_exame', 'corrigido_em')
    op.drop_column('lms_tentativa_exame', 'corrigido_por_usuario_id')
    op.drop_column('lms_tentativa_exame', 'correcoes_manuais')
    op.drop_column('lms_tentativa_exame', 'corrigida_finalizada')
