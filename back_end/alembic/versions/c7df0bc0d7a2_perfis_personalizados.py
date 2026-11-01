"""perfis_personalizados

Perfis da escola (bloco D2): cada escola cria perfis a partir da Secretaria
ou do Professor (ex.: "Tesouraria") com menos permissões — terceira camada
do Mapa de Permissões (app/core/mapa_permissoes.py).
- perfil_personalizado e perfil_personalizado_permissao, ambas com RLS;
- usuario.perfil_personalizado_id (apagar o perfil = volta ao perfil base).

Revision ID: c7df0bc0d7a2
Revises: 3757b96cc6bc
Create Date: 2026-10-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7df0bc0d7a2'
down_revision: Union[str, Sequence[str], None] = '3757b96cc6bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rls(tabela: str) -> None:
    op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
    op.execute(f"""
        CREATE POLICY isolamento_tenant_{tabela} ON {tabela}
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)


def upgrade() -> None:
    op.create_table('perfil_personalizado',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('nome', sa.String(length=60), nullable=False),
    sa.Column('perfil_base', sa.String(length=30), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'nome', name='uq_perfil_personalizado_tenant_nome')
    )
    op.create_index(op.f('ix_perfil_personalizado_tenant_id'), 'perfil_personalizado', ['tenant_id'], unique=False)
    _rls('perfil_personalizado')

    op.create_table('perfil_personalizado_permissao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('perfil_personalizado_id', sa.Uuid(), nullable=False),
    sa.Column('modulo', sa.String(length=80), nullable=False),
    sa.Column('pode_criar', sa.Boolean(), nullable=False),
    sa.Column('pode_ler', sa.Boolean(), nullable=False),
    sa.Column('pode_atualizar', sa.Boolean(), nullable=False),
    sa.Column('pode_apagar', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['perfil_personalizado_id'], ['perfil_personalizado.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('perfil_personalizado_id', 'modulo', name='uq_perfil_personalizado_modulo')
    )
    op.create_index(op.f('ix_perfil_personalizado_permissao_tenant_id'), 'perfil_personalizado_permissao', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_perfil_personalizado_permissao_perfil_personalizado_id'), 'perfil_personalizado_permissao', ['perfil_personalizado_id'], unique=False)
    _rls('perfil_personalizado_permissao')

    op.add_column('usuario', sa.Column('perfil_personalizado_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_usuario_perfil_personalizado_id'), 'usuario', ['perfil_personalizado_id'], unique=False)
    op.create_foreign_key('fk_usuario_perfil_personalizado', 'usuario', 'perfil_personalizado',
                          ['perfil_personalizado_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_usuario_perfil_personalizado', 'usuario', type_='foreignkey')
    op.drop_index(op.f('ix_usuario_perfil_personalizado_id'), table_name='usuario')
    op.drop_column('usuario', 'perfil_personalizado_id')
    for tabela in ('perfil_personalizado_permissao', 'perfil_personalizado'):
        op.execute(f"DROP POLICY IF EXISTS isolamento_tenant_{tabela} ON {tabela};")
    op.drop_index(op.f('ix_perfil_personalizado_permissao_perfil_personalizado_id'), table_name='perfil_personalizado_permissao')
    op.drop_index(op.f('ix_perfil_personalizado_permissao_tenant_id'), table_name='perfil_personalizado_permissao')
    op.drop_table('perfil_personalizado_permissao')
    op.drop_index(op.f('ix_perfil_personalizado_tenant_id'), table_name='perfil_personalizado')
    op.drop_table('perfil_personalizado')
