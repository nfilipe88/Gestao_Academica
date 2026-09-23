"""lms_variantes_modalidade_iniciar

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-17 14:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELAS_RLS = [
    ("lms_grupo_exame_atribuicao", "isolamento_tenant_lms_grupo_exame_atribuicao"),
]


def upgrade() -> None:
    """Upgrade schema."""
    # --- lms_exame: novas colunas (uma variante dentro de um grupo) ---
    op.add_column('lms_exame', sa.Column('grupo_id', sa.Uuid(), nullable=True))
    op.add_column('lms_exame', sa.Column('letra_variante', sa.String(length=5), server_default='A', nullable=False))
    op.add_column('lms_exame', sa.Column('modalidade', sa.String(length=20), server_default='PRESENCIAL', nullable=False))
    op.add_column('lms_exame', sa.Column('avaliacao_id', sa.Uuid(), nullable=True))
    op.add_column('lms_exame', sa.Column('iniciado', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('lms_exame', sa.Column('iniciado_em', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lms_exame', sa.Column('iniciado_por_usuario_id', sa.Uuid(), nullable=True))

    op.create_foreign_key(
        'fk_lms_exame_avaliacao_id', 'lms_exame', 'avaliacao', ['avaliacao_id'], ['id'], ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_lms_exame_iniciado_por_usuario_id', 'lms_exame', 'usuario', ['iniciado_por_usuario_id'], ['id'], ondelete='SET NULL'
    )

    # grupo_id: uma chave partilhada entre variantes irmãs (não FK — mesmo
    # padrão de Avaliacao.grupo_agendamento_id) — cada LMSExame já
    # existente vira o seu próprio grupo de 1 variante, por isso precisa
    # de um UUID DIFERENTE por linha (não dá para um único UPDATE SQL).
    conn = op.get_bind()
    ids = conn.execute(sa.text("SELECT id FROM lms_exame")).fetchall()
    for (exame_id,) in ids:
        conn.execute(
            sa.text("UPDATE lms_exame SET grupo_id = :g WHERE id = :i"),
            {"g": str(uuid.uuid4()), "i": str(exame_id)}
        )
    op.alter_column('lms_exame', 'grupo_id', nullable=False)
    op.create_index(op.f('ix_lms_exame_grupo_id'), 'lms_exame', ['grupo_id'], unique=False)

    # iniciado=True para exames que já têm tentativas reais — senão o
    # novo portão (publicado AND iniciado) bloquearia retroactivamente
    # exames já genuinamente em curso/concluídos antes desta funcionalidade.
    op.execute("""
        UPDATE lms_exame SET iniciado = true, iniciado_em = data_criacao
        WHERE id IN (SELECT DISTINCT exame_id FROM lms_tentativa_exame)
    """)

    # avaliacao_id fica nullable, sem backfill — ver docstring de
    # LMSExame.avaliacao_id em models_lms.py para o porquê (uma
    # Avaliação sintética por exame antigo não teria significado real
    # e bloquearia lançamento manual para essa turma+disciplina+período).

    # --- nova tabela: atribuição de aluno a variante ---
    op.create_table('lms_grupo_exame_atribuicao',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('grupo_id', sa.Uuid(), nullable=False),
    sa.Column('matricula_id', sa.Uuid(), nullable=False),
    sa.Column('exame_id', sa.Uuid(), nullable=False),
    sa.Column('atribuido_manualmente', sa.Boolean(), nullable=False),
    sa.Column('atribuido_em', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('atribuido_por_usuario_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['atribuido_por_usuario_id'], ['usuario.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['exame_id'], ['lms_exame.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['matricula_id'], ['matricula.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('grupo_id', 'matricula_id', name='uq_lms_grupo_atribuicao_matricula')
    )
    op.create_index(op.f('ix_lms_grupo_exame_atribuicao_tenant_id'), 'lms_grupo_exame_atribuicao', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_lms_grupo_exame_atribuicao_grupo_id'), 'lms_grupo_exame_atribuicao', ['grupo_id'], unique=False)

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

    op.drop_index(op.f('ix_lms_grupo_exame_atribuicao_grupo_id'), table_name='lms_grupo_exame_atribuicao')
    op.drop_index(op.f('ix_lms_grupo_exame_atribuicao_tenant_id'), table_name='lms_grupo_exame_atribuicao')
    op.drop_table('lms_grupo_exame_atribuicao')

    op.drop_index(op.f('ix_lms_exame_grupo_id'), table_name='lms_exame')
    op.drop_constraint('fk_lms_exame_iniciado_por_usuario_id', 'lms_exame', type_='foreignkey')
    op.drop_constraint('fk_lms_exame_avaliacao_id', 'lms_exame', type_='foreignkey')
    op.drop_column('lms_exame', 'iniciado_por_usuario_id')
    op.drop_column('lms_exame', 'iniciado_em')
    op.drop_column('lms_exame', 'iniciado')
    op.drop_column('lms_exame', 'avaliacao_id')
    op.drop_column('lms_exame', 'modalidade')
    op.drop_column('lms_exame', 'letra_variante')
    op.drop_column('lms_exame', 'grupo_id')
