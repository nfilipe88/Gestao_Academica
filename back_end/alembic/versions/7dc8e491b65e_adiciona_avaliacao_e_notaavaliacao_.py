"""Adiciona Avaliacao e NotaAvaliacao, RegistroNota.calculada_automaticamente

Revision ID: 7dc8e491b65e
Revises: f699505ccde4
Create Date: 2026-08-15 20:14:14.109749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dc8e491b65e'
down_revision: Union[str, Sequence[str], None] = 'f699505ccde4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nota: o autogenerate também detetou a remoção de um índice em
# "notificacao" (ix_notificacao_usuario_lida_data) — drift não
# relacionado com esta funcionalidade (não mexemos em Notificacao
# aqui), por isso foi propositadamente omitido desta migração.

TABELAS_RLS = [
    ("avaliacao", "isolamento_tenant_avaliacao"),
    ("nota_avaliacao", "isolamento_tenant_nota_avaliacao"),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('avaliacao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('turma_id', sa.Uuid(), nullable=False),
    sa.Column('disciplina_id', sa.Uuid(), nullable=False),
    sa.Column('periodo_avaliacao', sa.String(length=50), nullable=False),
    sa.Column('titulo', sa.String(length=150), nullable=False),
    sa.Column('tipo_avaliacao', sa.String(length=20), nullable=False),
    sa.Column('peso', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100'),
    sa.Column('data_avaliacao', sa.Date(), nullable=True),
    sa.Column('criado_por_usuario_id', sa.Uuid(), nullable=True),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['criado_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['disciplina_id'], ['disciplina.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['turma_id'], ['turma.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('nota_avaliacao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('avaliacao_id', sa.Uuid(), nullable=False),
    sa.Column('matricula_id', sa.Uuid(), nullable=False),
    sa.Column('valor_nota', sa.Numeric(precision=4, scale=2), nullable=False),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('data_atualizacao', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['avaliacao_id'], ['avaliacao.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('avaliacao_id', 'matricula_id', name='uq_nota_avaliacao_matricula')
    )
    # server_default aqui é só uma rede de segurança para os registos
    # já existentes (todos passam a "não calculada automaticamente",
    # o que é correto — são notas escritas à mão antes desta
    # funcionalidade existir); o modelo mantém o default=False do lado
    # do Python para os novos inserts.
    op.add_column('registro_nota', sa.Column('calculada_automaticamente', sa.Boolean(), nullable=False, server_default=sa.false()))

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

    op.drop_column('registro_nota', 'calculada_automaticamente')
    op.drop_table('nota_avaliacao')
    op.drop_table('avaliacao')
