"""Limite de alunos do plano SaaS (PlanoSaaS.limite_alunos) — até aqui
só informativo (mostrado na página de Preços); agora impede mesmo a
escola de ter mais alunos ATIVOS do que o plano da sua assinatura permite.

Regras:
- Só conta alunos ativos (Aluno.ativo) — um aluno desativado (ver
  cruds/alunos.py::alterar_estado_ativo_aluno) liberta a vaga, mas
  reativá-lo volta a ser validado aqui.
- Sem assinatura ATIVA, ou com plano sem limite (limite_alunos NULL), não
  há limite — o mesmo comportamento de antes desta funcionalidade.
- Tenant.isento_limite_alunos (concedido pelo Super Admin, ver
  cruds/admin.py::atualizar_isencao_limite_alunos) ignora o limite por
  completo, ex.: acordo comercial especial ou período de tolerância.
"""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant
from app.database.models_billing import AssinaturaTenant, PlanoSaaS
from app.database.models_pessoas import Aluno


async def garantir_vaga_para_alunos(db: AsyncSession, tenant_id, novos: int = 1) -> None:
    """Levanta 403 se ativar/criar `novos` alunos ultrapassar o limite do plano."""
    if novos <= 0:
        return

    isento = (await db.execute(select(Tenant.isento_limite_alunos).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if isento:
        return

    plano = (await db.execute(
        select(PlanoSaaS.nome, PlanoSaaS.limite_alunos)
        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoSaaS.id)
        .where(AssinaturaTenant.tenant_id == tenant_id, AssinaturaTenant.status == "ATIVA")
    )).first()
    if not plano or plano.limite_alunos is None:
        return

    ativos = (await db.execute(
        select(func.count(Aluno.id)).where(Aluno.tenant_id == tenant_id, Aluno.ativo == True)  # noqa: E712
    )).scalar_one()

    if ativos + novos > plano.limite_alunos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f'Limite de {plano.limite_alunos} aluno(s) ativo(s) do plano "{plano.nome}" atingido '
                f'({ativos} ativos). Desative alunos que já saíram da escola, ou contacte a plataforma '
                "para mudar de plano ou pedir uma isenção."
            ),
        )
