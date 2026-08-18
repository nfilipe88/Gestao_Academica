"""permissao_modulo

Revision ID: 584537bbba2e
Revises: e6be87fed8e2
Create Date: 2026-08-18 23:50:05.655748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '584537bbba2e'
down_revision: Union[str, Sequence[str], None] = 'e6be87fed8e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Semente: mesma matriz que vivia hardcoded em
# permissoes.component.ts::MODULOS antes desta migração — só passa a
# ser editável a partir de agora, os valores iniciais são os mesmos.
# NENHUM/LEITURA/PARCIAL/TOTAL são traduzidos para flags CRUD por
# PERMISSOES_POR_NIVEL abaixo; quem editar uma célula na UI passa a
# controlar cada operação (Criar/Ler/Atualizar/Apagar) em separado.
PERFIS = ["super_admin", "gestor", "secretaria", "professor", "aluno_responsavel"]

PERMISSOES_POR_NIVEL = {
    "NENHUM":  {"pode_criar": False, "pode_ler": False, "pode_atualizar": False, "pode_apagar": False},
    "LEITURA": {"pode_criar": False, "pode_ler": True,  "pode_atualizar": False, "pode_apagar": False},
    "PARCIAL": {"pode_criar": False, "pode_ler": True,  "pode_atualizar": True,  "pode_apagar": False},
    "TOTAL":   {"pode_criar": True,  "pode_ler": True,  "pode_atualizar": True,  "pode_apagar": True},
}

MODULOS = [
    ("Visão Geral",                    ["NENHUM", "LEITURA", "LEITURA", "LEITURA", "NENHUM"]),
    ("Cursos",                         ["NENHUM", "TOTAL",   "TOTAL",   "LEITURA", "NENHUM"]),
    ("Turmas & Matrículas",            ["NENHUM", "TOTAL",   "TOTAL",   "LEITURA", "NENHUM"]),
    ("Alunos & Responsáveis",          ["NENHUM", "TOTAL",   "TOTAL",   "LEITURA", "NENHUM"]),
    ("Diário de Classe",               ["NENHUM", "TOTAL",   "TOTAL",   "PARCIAL", "NENHUM"]),
    ("Trabalhos / Tarefas",            ["NENHUM", "TOTAL",   "TOTAL",   "PARCIAL", "NENHUM"]),
    ("Horários",                       ["NENHUM", "TOTAL",   "TOTAL",   "LEITURA", "NENHUM"]),
    ("Comunicações",                   ["NENHUM", "TOTAL",   "TOTAL",   "PARCIAL", "NENHUM"]),
    ("Documentos (interno)",           ["NENHUM", "TOTAL",   "PARCIAL", "PARCIAL", "NENHUM"]),
    ("CRM",                            ["NENHUM", "TOTAL",   "TOTAL",   "NENHUM",  "NENHUM"]),
    ("Financeiro",                     ["NENHUM", "TOTAL",   "TOTAL",   "NENHUM",  "NENHUM"]),
    ("Transferências de Alunos",       ["PARCIAL", "PARCIAL", "PARCIAL", "NENHUM", "NENHUM"]),
    ("Professores",                    ["NENHUM", "TOTAL",   "PARCIAL", "LEITURA", "NENHUM"]),
    ("Indicadores",                    ["NENHUM", "TOTAL",   "TOTAL",   "NENHUM",  "NENHUM"]),
    ("Configurações",                  ["NENHUM", "TOTAL",   "NENHUM",  "NENHUM",  "NENHUM"]),
    ("Portal (próprio / educandos)",   ["NENHUM", "NENHUM",  "NENHUM",  "NENHUM",  "TOTAL"]),
    ("Instituições (multi-escola)",    ["TOTAL",  "NENHUM",  "NENHUM",  "NENHUM",  "NENHUM"]),
]


def upgrade() -> None:
    """Upgrade schema."""
    # NOTA: o autogenerate também detetou 'ix_notificacao_usuario_lida_data'
    # como removido — drift pré-existente e sem relação com esta mudança
    # (ver a mesma nota nas migrações anteriores).
    op.create_table('permissao_modulo',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.Column('modulo', sa.String(length=80), nullable=False),
    sa.Column('perfil', sa.String(length=30), nullable=False),
    sa.Column('pode_criar', sa.Boolean(), nullable=False),
    sa.Column('pode_ler', sa.Boolean(), nullable=False),
    sa.Column('pode_atualizar', sa.Boolean(), nullable=False),
    sa.Column('pode_apagar', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('modulo', 'perfil', name='uq_permissao_modulo_perfil')
    )

    permissao_modulo = sa.table(
        'permissao_modulo',
        sa.column('id', sa.Uuid()),
        sa.column('ordem', sa.Integer()),
        sa.column('modulo', sa.String()),
        sa.column('perfil', sa.String()),
        sa.column('pode_criar', sa.Boolean()),
        sa.column('pode_ler', sa.Boolean()),
        sa.column('pode_atualizar', sa.Boolean()),
        sa.column('pode_apagar', sa.Boolean()),
    )

    import uuid as _uuid
    linhas = []
    for ordem, (modulo, niveis) in enumerate(MODULOS):
        for perfil, nivel in zip(PERFIS, niveis):
            linhas.append({
                "id": _uuid.uuid4(), "ordem": ordem, "modulo": modulo, "perfil": perfil,
                **PERMISSOES_POR_NIVEL[nivel],
            })
    op.bulk_insert(permissao_modulo, linhas)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('permissao_modulo')
