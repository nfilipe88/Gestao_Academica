"""Introduz Serie_Ano entre Curso e Turma

Revision ID: 890a1123688a
Revises: a004a09626ba
Create Date: 2026-08-09 21:52:27.169021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '890a1123688a'
down_revision: Union[str, Sequence[str], None] = 'a004a09626ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. CRIAÇÃO DA TABELA serie_ano
    # ---------------------------------------------------------
    op.create_table('serie_ano',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('curso_id', sa.UUID(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),

        sa.ForeignKeyConstraint(['curso_id'], ['curso.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("ALTER TABLE serie_ano ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_serie_ano ON serie_ano
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)

    # ---------------------------------------------------------
    # 2. ADICIONAR serie_ano_id A turma (nullable por agora, para o backfill)
    # ---------------------------------------------------------
    op.add_column('turma', sa.Column('serie_ano_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'turma_serie_ano_id_fkey', 'turma', 'serie_ano',
        ['serie_ano_id'], ['id'], ondelete='CASCADE'
    )

    # ---------------------------------------------------------
    # 3. BACKFILL: turmas já existentes (ex: de testes) não têm
    # serie_ano_id. Criamos uma Série/Ano genérica ("Ano Único") por cada
    # curso que já tinha turmas, e associamo-las lá, para não perder dados.
    # ---------------------------------------------------------
    op.execute("""
        INSERT INTO serie_ano (id, tenant_id, curso_id, nome)
        SELECT gen_random_uuid(), tenant_id, curso_id, 'Ano Único'
        FROM (SELECT DISTINCT tenant_id, curso_id FROM turma) AS cursos_com_turma;
    """)
    op.execute("""
        UPDATE turma
        SET serie_ano_id = serie_ano.id
        FROM serie_ano
        WHERE turma.curso_id = serie_ano.curso_id
          AND turma.tenant_id = serie_ano.tenant_id
          AND serie_ano.nome = 'Ano Único';
    """)

    # ---------------------------------------------------------
    # 4. Tornar serie_ano_id obrigatório e remover curso_id de turma
    # ---------------------------------------------------------
    op.alter_column('turma', 'serie_ano_id', nullable=False)
    op.drop_constraint('turma_curso_id_fkey', 'turma', type_='foreignkey')
    op.drop_column('turma', 'curso_id')


def downgrade() -> None:
    # Reconstituir curso_id a partir de serie_ano.curso_id
    op.add_column('turma', sa.Column('curso_id', sa.UUID(), nullable=True))
    op.execute("""
        UPDATE turma
        SET curso_id = serie_ano.curso_id
        FROM serie_ano
        WHERE turma.serie_ano_id = serie_ano.id;
    """)
    op.alter_column('turma', 'curso_id', nullable=False)
    op.create_foreign_key(
        'turma_curso_id_fkey', 'turma', 'curso',
        ['curso_id'], ['id'], ondelete='CASCADE'
    )

    op.drop_constraint('turma_serie_ano_id_fkey', 'turma', type_='foreignkey')
    op.drop_column('turma', 'serie_ano_id')

    op.execute("DROP POLICY IF EXISTS isolamento_tenant_serie_ano ON serie_ano;")
    op.execute("ALTER TABLE serie_ano DISABLE ROW LEVEL SECURITY;")
    op.drop_table('serie_ano')
