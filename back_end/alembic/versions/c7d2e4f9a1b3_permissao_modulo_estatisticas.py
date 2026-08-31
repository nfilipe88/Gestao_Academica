"""permissao_modulo_estatisticas

Revision ID: c7d2e4f9a1b3
Revises: b6b531009123
Create Date: 2026-08-31 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid as _uuid

# revision identifiers, used by Alembic.
revision: str = 'c7d2e4f9a1b3'
down_revision: Union[str, Sequence[str], None] = 'b6b531009123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Acrescenta "Estatísticas" (Dashboard + Relatório por período,
# export .xlsx/.xls — ver app/cruds/estatisticas.py) ao Mapa de
# Permissões — mesmos níveis de "Indicadores" (o módulo mais próximo:
# visão executiva agregada, sem nada disto ser visível no Portal da
# família). Ao contrário de Indicadores, este módulo não está (ainda)
# gateado por plano em app/core/modulos.py — essa é uma decisão de
# produto separada da documentação no mapa.
PERFIS = ["super_admin", "gestor", "secretaria", "professor", "aluno_responsavel"]

PERMISSOES_POR_NIVEL = {
    "NENHUM":  {"pode_criar": False, "pode_ler": False, "pode_atualizar": False, "pode_apagar": False},
    "TOTAL":   {"pode_criar": True,  "pode_ler": True,  "pode_atualizar": True,  "pode_apagar": True},
}

NOVO_MODULO = ("Estatísticas", ["NENHUM", "TOTAL", "TOTAL", "NENHUM", "NENHUM"])

# Inserido logo a seguir a "Indicadores" (ordem 14) — as restantes
# linhas (ordem 15 em diante) sobem uma posição para abrir espaço.
NOVA_ORDEM = 15


def upgrade() -> None:
    """Upgrade schema."""
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

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE permissao_modulo SET ordem = ordem + 1 WHERE ordem >= :ordem"),
        {"ordem": NOVA_ORDEM},
    )

    modulo, niveis = NOVO_MODULO
    linhas = [
        {"id": _uuid.uuid4(), "ordem": NOVA_ORDEM, "modulo": modulo, "perfil": perfil, **PERMISSOES_POR_NIVEL[nivel]}
        for perfil, nivel in zip(PERFIS, niveis)
    ]
    op.bulk_insert(permissao_modulo, linhas)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM permissao_modulo WHERE modulo = :modulo"), {"modulo": NOVO_MODULO[0]})
    conn.execute(
        sa.text("UPDATE permissao_modulo SET ordem = ordem - 1 WHERE ordem > :ordem"),
        {"ordem": NOVA_ORDEM},
    )
