"""mapa_permissoes_real

O Mapa de Permissões passa a decidir o acesso (app/core/mapa_permissoes.py):
- tabela permissao_modulo_escola: restrições de cada escola (o Gestor), RLS;
- o mapa base é alinhado com o que o código realmente permitia neste dia
  (ninguém ganha nem perde acesso), com UMA exceção decidida: o Professor
  deixa de ter acesso ao Financeiro (o mapa sempre o disse; o código não).
Linhas do mapa sem rotas (Visão Geral, Instituições) ficam como estavam.

Revision ID: 3757b96cc6bc
Revises: 8481eed915e9
Create Date: 2026-10-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3757b96cc6bc'
down_revision: Union[str, Sequence[str], None] = '8481eed915e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (módulo, coluna do perfil): operações C R U D que o código permitia.
_ALINHADO = {
    ('Alunos & Responsáveis', 'aluno_responsavel'): '----',
    ('Alunos & Responsáveis', 'gestor'): 'CRUD',
    ('Alunos & Responsáveis', 'professor'): '-R--',
    ('Alunos & Responsáveis', 'secretaria'): 'CR-D',
    ('Alunos & Responsáveis', 'super_admin'): '----',
    ('CRM', 'aluno_responsavel'): '----',
    ('CRM', 'gestor'): 'CRU-',
    ('CRM', 'professor'): '----',
    ('CRM', 'secretaria'): 'CRU-',
    ('CRM', 'super_admin'): '----',
    ('Comportamento', 'aluno_responsavel'): '----',
    ('Comportamento', 'gestor'): 'CR-D',
    ('Comportamento', 'professor'): 'CR-D',
    ('Comportamento', 'secretaria'): 'CR-D',
    ('Comportamento', 'super_admin'): '----',
    ('Comunicações', 'aluno_responsavel'): '----',
    ('Comunicações', 'gestor'): 'CRU-',
    ('Comunicações', 'professor'): 'CRU-',
    ('Comunicações', 'secretaria'): 'CRU-',
    ('Comunicações', 'super_admin'): '----',
    ('Configurações', 'aluno_responsavel'): '-R--',
    ('Configurações', 'gestor'): 'CRUD',
    ('Configurações', 'professor'): '-R--',
    ('Configurações', 'secretaria'): '-R--',
    ('Configurações', 'super_admin'): '-R--',
    ('Cursos', 'aluno_responsavel'): '----',
    ('Cursos', 'gestor'): 'CRU-',
    ('Cursos', 'professor'): '-R--',
    ('Cursos', 'secretaria'): 'CRU-',
    ('Cursos', 'super_admin'): '----',
    ('Diário de Classe', 'aluno_responsavel'): '----',
    ('Diário de Classe', 'gestor'): 'CRUD',
    ('Diário de Classe', 'professor'): 'CRUD',
    ('Diário de Classe', 'secretaria'): 'CRUD',
    ('Diário de Classe', 'super_admin'): '----',
    ('Documentos (interno)', 'aluno_responsavel'): 'CRU-',
    ('Documentos (interno)', 'gestor'): 'CRUD',
    ('Documentos (interno)', 'professor'): 'CRU-',
    ('Documentos (interno)', 'secretaria'): 'CRU-',
    ('Documentos (interno)', 'super_admin'): 'CRU-',
    ('Estatísticas', 'aluno_responsavel'): '----',
    ('Estatísticas', 'gestor'): '-R--',
    ('Estatísticas', 'professor'): '----',
    ('Estatísticas', 'secretaria'): '-R--',
    ('Estatísticas', 'super_admin'): '----',
    ('Financeiro', 'aluno_responsavel'): 'CRU-',
    ('Financeiro', 'gestor'): 'CRUD',
    # Fechado de propósito (decisão de 2026-10-19): o código deixava o Professor ver
    # faturas/contratos de todas as famílias, gerar cobranças e reportar pagamentos.
    ('Financeiro', 'professor'): '----',
    ('Financeiro', 'secretaria'): 'CRUD',
    ('Financeiro', 'super_admin'): 'CRU-',
    ('Horários', 'aluno_responsavel'): '----',
    ('Horários', 'gestor'): 'CRUD',
    ('Horários', 'professor'): '-R--',
    ('Horários', 'secretaria'): 'CRUD',
    ('Horários', 'super_admin'): '----',
    ('Indicadores', 'aluno_responsavel'): '----',
    ('Indicadores', 'gestor'): 'CR--',
    ('Indicadores', 'professor'): '----',
    ('Indicadores', 'secretaria'): 'CR--',
    ('Indicadores', 'super_admin'): '----',
    ('Portal (próprio / educandos)', 'aluno_responsavel'): 'CR--',
    ('Portal (próprio / educandos)', 'gestor'): '----',
    ('Portal (próprio / educandos)', 'professor'): '----',
    ('Portal (próprio / educandos)', 'secretaria'): '----',
    ('Portal (próprio / educandos)', 'super_admin'): '----',
    ('Professores', 'aluno_responsavel'): '----',
    ('Professores', 'gestor'): 'CR--',
    ('Professores', 'professor'): '-R--',
    ('Professores', 'secretaria'): 'CR--',
    ('Professores', 'super_admin'): '----',
    ('Trabalhos / Tarefas', 'aluno_responsavel'): '----',
    ('Trabalhos / Tarefas', 'gestor'): 'CRUD',
    ('Trabalhos / Tarefas', 'professor'): 'CRUD',
    ('Trabalhos / Tarefas', 'secretaria'): 'CRUD',
    ('Trabalhos / Tarefas', 'super_admin'): '----',
    ('Transferências de Alunos', 'aluno_responsavel'): '----',
    ('Transferências de Alunos', 'gestor'): 'CRU-',
    ('Transferências de Alunos', 'professor'): '----',
    ('Transferências de Alunos', 'secretaria'): 'CRU-',
    ('Transferências de Alunos', 'super_admin'): '-R--',
    ('Turmas & Matrículas', 'aluno_responsavel'): '----',
    ('Turmas & Matrículas', 'gestor'): 'CRUD',
    ('Turmas & Matrículas', 'professor'): '-R--',
    ('Turmas & Matrículas', 'secretaria'): 'CRUD',
    ('Turmas & Matrículas', 'super_admin'): '----',
}


def upgrade() -> None:
    op.create_table('permissao_modulo_escola',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('modulo', sa.String(length=80), nullable=False),
    sa.Column('perfil', sa.String(length=30), nullable=False),
    sa.Column('pode_criar', sa.Boolean(), nullable=False),
    sa.Column('pode_ler', sa.Boolean(), nullable=False),
    sa.Column('pode_atualizar', sa.Boolean(), nullable=False),
    sa.Column('pode_apagar', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'modulo', 'perfil', name='uq_permissao_escola_modulo_perfil')
    )
    op.create_index(op.f('ix_permissao_modulo_escola_tenant_id'), 'permissao_modulo_escola', ['tenant_id'], unique=False)
    op.execute("ALTER TABLE permissao_modulo_escola ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY isolamento_tenant_permissao_modulo_escola ON permissao_modulo_escola
        USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
    """)

    tabela = sa.table('permissao_modulo', sa.column('modulo', sa.String), sa.column('perfil', sa.String),
                      sa.column('pode_criar', sa.Boolean), sa.column('pode_ler', sa.Boolean),
                      sa.column('pode_atualizar', sa.Boolean), sa.column('pode_apagar', sa.Boolean))
    for (modulo, perfil), letras in _ALINHADO.items():
        op.execute(tabela.update()
                   .where(tabela.c.modulo == modulo, tabela.c.perfil == perfil)
                   .values(pode_criar=letras[0] == 'C', pode_ler=letras[1] == 'R',
                           pode_atualizar=letras[2] == 'U', pode_apagar=letras[3] == 'D'))


def downgrade() -> None:
    # O alinhamento do mapa base não é revertido (o mapa antigo era só documentação).
    op.execute("DROP POLICY IF EXISTS isolamento_tenant_permissao_modulo_escola ON permissao_modulo_escola;")
    op.drop_index(op.f('ix_permissao_modulo_escola_tenant_id'), table_name='permissao_modulo_escola')
    op.drop_table('permissao_modulo_escola')
