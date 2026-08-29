"""
Controlo de acesso por módulo, conforme o plano SaaS da escola —
distinto do RBAC por perfil (app/core/security.py::exigir_perfil): ali
é "que PERFIL pode usar isto", aqui é "esta ESCOLA paga por isto".

Nem todos os módulos são gateáveis — os fundamentais para sequer usar
a plataforma (Alunos, Turmas, Cursos, Configurações, Diário, Portal,
...) ficam sempre acessíveis, independentemente do plano; só os de
maior valor comercial (mais próximos de "add-on premium" do que de
"administração escolar básica") é que dependem de estarem incluídos
no plano da escola. Usa a MESMA lista de módulos do Mapa de Permissões
(ver alembic/versions/584537bbba2e_permissao_modulo.py::MODULOS) —
um só vocabulário de "módulo" em toda a plataforma.

Sem assinatura definida para o tenant (escola sem plano atribuído
ainda, ou criada antes desta funcionalidade existir): acesso total a
tudo — falha aberta de propósito, para nunca bloquear uma escola já a
usar a plataforma só porque o Super Admin ainda não lhe atribuiu um
plano formalmente.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import obter_utilizador_atual
from app.database.session import obter_sessao_db
from app.database.models_billing import AssinaturaTenant, PlanoSaaSModulo

MODULOS_GATEAVEIS = {
    "CRM", "Financeiro", "Indicadores", "Comunicações", "Horários",
    "Diário de Classe", "Trabalhos / Tarefas", "Transferências de Alunos", "Professores",
}


async def _modulos_incluidos_do_tenant(db: AsyncSession, tenant_id) -> set[str] | None:
    """None = sem assinatura definida (falha aberta, tudo liberado)."""
    assinatura = (await db.execute(
        select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant_id, AssinaturaTenant.status == "ATIVA")
    )).scalars().first()
    if not assinatura:
        return None

    modulos = (await db.execute(
        select(PlanoSaaSModulo.modulo).where(PlanoSaaSModulo.plano_id == assinatura.plano_id)
    )).scalars().all()
    return set(modulos)


def exigir_modulo(nome_modulo: str):
    """Fábrica de dependência — uso: adicionar
    dependencies=[Depends(exigir_modulo("Financeiro"))] ao
    app.include_router(...) desse módulo em main.py (bloqueia TODAS as
    rotas desse router de uma vez, não é preciso repetir por endpoint).

    SUPER_ADMIN nunca é bloqueado — não pertence a nenhuma escola
    cliente, o conceito de "plano" não se aplica a ele."""
    async def verificar(
        utilizador: dict = Depends(obter_utilizador_atual),
        db: AsyncSession = Depends(obter_sessao_db),
    ) -> None:
        if utilizador["perfil_acesso"] == "SUPER_ADMIN":
            return
        modulos_incluidos = await _modulos_incluidos_do_tenant(db, utilizador["tenant_id"])
        if modulos_incluidos is not None and nome_modulo not in modulos_incluidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'O módulo "{nome_modulo}" não está incluído no plano desta instituição. '
                       f"Contacte a direção da escola ou o suporte para o adicionar."
            )
    return verificar
