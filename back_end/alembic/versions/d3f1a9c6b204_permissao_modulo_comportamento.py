"""permissao_modulo_comportamento

Revision ID: d3f1a9c6b204
Revises: caaf99ee3335
Create Date: 2026-08-30 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid as _uuid

# revision identifiers, used by Alembic.
revision: str = 'd3f1a9c6b204'
down_revision: Union[str, Sequence[str], None] = 'caaf99ee3335'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Acrescenta "Comportamento" (ver app/cruds/comportamento.py, sessão
# que introduziu o módulo) ao Mapa de Permissões — não existia ainda
# porque o módulo em si não existia quando a matriz original foi
# semeada (ver 584537bbba2e_permissao_modulo.py).
#
# Níveis escolhidos: exatamente os mesmos de "Diário de Classe" (o
# módulo comercial de que Comportamento faz parte — ver
# app/core/modulos.py, gateado como "Diário de Classe", não um módulo
# à parte), com uma única diferença: aluno_responsavel passa de NENHUM
# para LEITURA — ao contrário do resto do Diário, o resumo de
# Comportamento É mostrado ao encarregado/aluno no Dashboard do Portal
# (ver cruds/portal.py::obter_estatisticas_do_educando).
#
# Professor = PARCIAL (ler+atualizar, sem criar/apagar) segue a mesma
# convenção já usada na linha de Diário de Classe: aqui "atualizar"
# representa o lançamento do dia a dia (registar um incidente), não
# uma operação de configuração administrativa — o mapa é uma
# documentação aproximada do RBAC real, não uma cópia bit a bit (ver
# docstring de models_permissoes.py); a matriz não tem como capturar a
# nuance extra de "só remove os registos que o próprio criou", mesmo
# tendo pode_apagar=False aqui.
PERFIS = ["super_admin", "gestor", "secretaria", "professor", "aluno_responsavel"]

PERMISSOES_POR_NIVEL = {
    "NENHUM":  {"pode_criar": False, "pode_ler": False, "pode_atualizar": False, "pode_apagar": False},
    "LEITURA": {"pode_criar": False, "pode_ler": True,  "pode_atualizar": False, "pode_apagar": False},
    "PARCIAL": {"pode_criar": False, "pode_ler": True,  "pode_atualizar": True,  "pode_apagar": False},
    "TOTAL":   {"pode_criar": True,  "pode_ler": True,  "pode_atualizar": True,  "pode_apagar": True},
}

NOVO_MODULO = ("Comportamento", ["NENHUM", "TOTAL", "TOTAL", "PARCIAL", "LEITURA"])

# Inserido logo a seguir a "Diário de Classe" (ordem 4) — as restantes
# linhas (ordem 5 em diante) sobem uma posição para abrir espaço.
NOVA_ORDEM = 5


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
