"""Adiciona ProfessorTurmaDisciplina, RegistroFrequencia, RegistroNota e Auditoria

Revision ID: 4bb16f8e6da2
Revises: 2107cb3896fc
Create Date: 2026-08-11 23:59:34.388336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bb16f8e6da2'
down_revision: Union[str, Sequence[str], None] = '2107cb3896fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELAS_RLS = [
    ("professor_turma_disciplina", "isolamento_tenant_ptd"),
    ("registro_frequencia", "isolamento_tenant_frequencia"),
    ("registro_nota", "isolamento_tenant_nota"),
    ("registro_nota_auditoria", "isolamento_tenant_nota_auditoria"),
]


def upgrade() -> None:
    op.create_table('professor_turma_disciplina',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('professor_id', sa.UUID(), nullable=False),
        sa.Column('turma_id', sa.UUID(), nullable=False),
        sa.Column('disciplina_id', sa.UUID(), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['professor_id'], ['professor.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['turma_id'], ['turma.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('professor_id', 'turma_id', 'disciplina_id', name='uq_alocacao_professor_turma_disciplina')
    )

    op.create_table('registro_frequencia',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('matricula_id', sa.UUID(), nullable=False),
        sa.Column('disciplina_id', sa.UUID(), nullable=False),
        sa.Column('data_aula', sa.Date(), nullable=False),
        sa.Column('quantidade_aulas', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('conteudo_programado', sa.String(length=500), nullable=True),
        sa.Column('presenca', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('faltas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('matricula_id', 'disciplina_id', 'data_aula', name='uq_frequencia_matricula_disciplina_data')
    )

    op.create_table('registro_nota',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('matricula_id', sa.UUID(), nullable=False),
        sa.Column('disciplina_id', sa.UUID(), nullable=False),
        sa.Column('periodo_avaliacao', sa.String(length=50), nullable=False),
        sa.Column('tipo_avaliacao', sa.String(length=50), nullable=True),
        sa.Column('data_avaliacao', sa.Date(), nullable=True),
        sa.Column('valor_nota', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('data_atualizacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('matricula_id', 'disciplina_id', 'periodo_avaliacao', name='uq_nota_matricula_disciplina_periodo')
    )

    op.create_table('registro_nota_auditoria',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('registro_nota_id', sa.UUID(), nullable=False),
        sa.Column('alterado_por', sa.UUID(), nullable=True),
        sa.Column('valor_antigo', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('valor_novo', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('alterado_em', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registro_nota_id'], ['registro_nota.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['alterado_por'], ['usuario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    for tabela, policy in TABELAS_RLS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY {policy} ON {tabela}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
        """)


def downgrade() -> None:
    for tabela, policy in reversed(TABELAS_RLS):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {tabela};")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY;")

    op.drop_table('registro_nota_auditoria')
    op.drop_table('registro_nota')
    op.drop_table('registro_frequencia')
    op.drop_table('professor_turma_disciplina')
