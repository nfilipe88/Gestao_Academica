from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi import Depends
from app.core.security import obter_utilizador_atual, exigir_perfil
from typing import Dict, Any, AsyncGenerator
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

# Duas ligações distintas, dois roles Postgres distintos — ver
# scripts/criar_roles_rls.sql para os criar.
#
# DATABASE_URL (role app_tenant, SEM bypassrls): todo o tráfego normal
# passa por aqui. O Postgres aplica de facto as policies
# isolamento_tenant_* (ver alembic/versions/*) — antes desta mudança a
# app ligava como superuser (`postgres`), que ignora RLS sempre,
# independentemente do que as policies diziam; o isolamento entre
# escolas dependia inteiramente do WHERE tenant_id=... em cada crud.
# Continua a depender disso (é a defesa principal), mas agora o RLS é
# uma segunda camada real, não decorativa.
#
# DATABASE_URL_SISTEMA (role app_sistema, COM bypassrls, sem
# superuser): só para as poucas operações que são, por natureza,
# anteriores/exteriores a um tenant concreto — nunca para servir
# pedidos normais de utilizadores autenticados de uma escola.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Crie um ficheiro .env na raiz do back_end "
        "com base no .env.example."
    )

DATABASE_URL_SISTEMA = os.getenv("DATABASE_URL_SISTEMA")
if not DATABASE_URL_SISTEMA:
    raise RuntimeError(
        "DATABASE_URL_SISTEMA não encontrada. Crie um ficheiro .env na raiz do back_end "
        "com base no .env.example (precisa do role app_sistema — ver scripts/criar_roles_rls.sql)."
    )

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

engine_sistema = create_async_engine(DATABASE_URL_SISTEMA, echo=False)
AsyncSessionLocalSistema = async_sessionmaker(bind=engine_sistema, class_=AsyncSession, expire_on_commit=False)


async def obter_sessao_db(
    utilizador: Dict[str, Any] = Depends(obter_utilizador_atual)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Injeta a sessão do banco de dados (role app_tenant) e configura a
    variável de sessão do Postgres para ativar o Row Level Security
    (RLS) automaticamente para o Tenant ativo.
    """
    async with AsyncSessionLocal() as sessao:
        # EXECUÇÃO CRÍTICA: Injeta o tenant_id na sessão atual do PostgreSQL
        # Nota: "SET LOCAL x = :param" NÃO é válido em Postgres — SET/SET
        # LOCAL não aceitam parâmetros vinculados ($1), só literais, o que
        # dava sempre "syntax error at or near '$1'" (500 em todos os
        # endpoints académicos). set_config() é a forma correta de definir
        # uma GUC parametrizada.
        #
        # O 3º argumento é `false` (âmbito da SESSÃO, não `true`/LOCAL —
        # âmbito da transação): muitos cruds fazem `db.commit()` a meio
        # do pedido e continuam a usar a mesma sessão a seguir (ex.:
        # `await db.refresh(objeto)` depois do commit, para devolver os
        # valores gerados pelo servidor) — com âmbito LOCAL, o commit
        # já tinha "esquecido" o tenant_id nesse ponto, e a policy de
        # RLS rebentava com "invalid input syntax for type uuid: ''" ao
        # comparar tenant_id com uma current_setting entretanto vazia.
        # Isto só passou a aparecer agora que o RLS é mesmo aplicado
        # (ver DATABASE_URL acima) — como ligação pooled que é, o valor
        # de sessão tem de ser limpo explicitamente no `finally` abaixo,
        # para o próximo pedido a reutilizar esta ligação nunca herdar
        # por engano o tenant_id de um pedido anterior.
        tenant_str = str(utilizador["tenant_id"])
        await sessao.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_str}
        )

        try:
            yield sessao
        finally:
            try:
                # Se o pedido acabou por uma exceção a meio de uma
                # transação, a ligação pode estar "abortada" (Postgres
                # recusa qualquer comando até um ROLLBACK) — sem isto, o
                # set_config de limpeza a seguir falhava sempre nesse caso.
                await sessao.rollback()
                # SET (mesmo sem LOCAL) aplica-se imediatamente, sem
                # depender de commit — só precisa de correr antes de a
                # ligação voltar para o pool.
                await sessao.execute(text("SELECT set_config('app.current_tenant_id', '', false)"))
            except Exception:
                pass  # a ligação vai de qualquer forma ser fechada a seguir
            await sessao.close()


# Só o Super Admin — o painel dele é inerentemente cross-tenant (lista
# TODAS as escolas, gere utilizadores de QUALQUER escola). Sob
# app_tenant isto não daria para fazer sem reescrever cada leitura
# num ciclo por tenant só para poder ir trocando app.current_tenant_id
# — em vez disso, usa app_sistema (bypassrls), gated pelo próprio
# exigir_perfil("SUPER_ADMIN") logo na dependency, antes de a rota
# sequer correr.
_exigir_super_admin = exigir_perfil("SUPER_ADMIN")


async def obter_sessao_db_admin(
    utilizador: Dict[str, Any] = Depends(_exigir_super_admin)
) -> AsyncGenerator[AsyncSession, None]:
    """Sessão cross-tenant (role app_sistema) para o Painel Super Admin — ver app/api/v1/admin.py."""
    async with AsyncSessionLocalSistema() as sessao:
        try:
            yield sessao
        finally:
            await sessao.close()


async def obter_sessao_db_publica() -> AsyncGenerator[AsyncSession, None]:
    """
    Sessão sem utilizador autenticado (role app_sistema, bypassrls),
    para rotas verdadeiramente públicas:
      - captação pública de Lead (CRM) — o tenant_id vem do path da
        URL, e o crud já faz set_config('app.current_tenant_id', ...)
        explicitamente assim que o descobre (cruds/crm.py::criar_lead_publico);
      - webhook de pagamento (PayPal) — o tenant só é conhecido DEPOIS
        de encontrar a Transacao_Gateway pelo gateway_transaction_id,
        uma busca que é, por definição, cross-tenant (não há tenant_id
        nenhum disponível antes dela).
    Continua a valer a mesma disciplina de sempre filtrar
    explicitamente por tenant_id nas queries — bypassrls tira a rede de
    segurança do RLS, não a validação normal dos cruds.
    """
    async with AsyncSessionLocalSistema() as sessao:
        try:
            yield sessao
        finally:
            await sessao.close()
