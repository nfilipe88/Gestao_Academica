"""lms exames

Revision ID: acc8c8ec166f
Revises: 674b992b82ff
Create Date: 2026-08-18 22:23:33.380546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acc8c8ec166f'
down_revision: Union[str, Sequence[str], None] = '674b992b82ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [
    ("lms_questao", "isolamento_tenant_lms_questao"),
    ("lms_exame", "isolamento_tenant_lms_exame"),
    ("lms_exame_questao", "isolamento_tenant_lms_exame_questao"),
    ("lms_tentativa_exame", "isolamento_tenant_lms_tentativa_exame"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança,
    # por isso excluído desta migração (ver mesma nota nas duas migrações
    # anteriores).
    op.create_table('lms_questao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('disciplina_id', sa.Uuid(), nullable=False),
    sa.Column('enunciado', sa.Text(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('opcoes', sa.JSON(), nullable=False),
    sa.Column('resposta_correta', sa.String(length=500), nullable=False),
    sa.Column('valor', sa.Numeric(precision=4, scale=2), nullable=False),
    sa.Column('criado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lms_exame',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('alocacao_id', sa.Uuid(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('data_inicio', sa.DateTime(timezone=True), nullable=False),
    sa.Column('data_fim', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duracao_minutos', sa.Integer(), nullable=False),
    sa.Column('baralhar_perguntas', sa.Boolean(), nullable=False),
    sa.Column('publicado', sa.Boolean(), nullable=False),
    sa.Column('criado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['alocacao_id'], ['professor_turma_disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lms_exame_questao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('exame_id', sa.Uuid(), nullable=False),
    sa.Column('questao_id', sa.Uuid(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['exame_id'], ['lms_exame.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['questao_id'], ['lms_questao.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('exame_id', 'ordem', name='uq_lms_exame_questao_exame_ordem'),
    sa.UniqueConstraint('exame_id', 'questao_id', name='uq_lms_exame_questao_exame_questao')
    )
    op.create_table('lms_tentativa_exame',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('exame_id', sa.Uuid(), nullable=False),
    sa.Column('matricula_id', sa.Uuid(), nullable=False),
    sa.Column('ordem_questoes', sa.JSON(), nullable=False),
    sa.Column('respostas', sa.JSON(), nullable=False),
    sa.Column('nota_obtida', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('nota_maxima', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('eventos_suspeitos', sa.Integer(), nullable=False),
    sa.Column('data_inicio', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('data_submissao', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['exame_id'], ['lms_exame.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('exame_id', 'matricula_id', name='uq_lms_tentativa_exame_exame_matricula')
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

    op.drop_table('lms_tentativa_exame')
    op.drop_table('lms_exame_questao')
    op.drop_table('lms_exame')
    op.drop_table('lms_questao')
