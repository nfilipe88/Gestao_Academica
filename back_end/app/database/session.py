from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncConnection
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

    IMPORTANTE — porque isto usa engine.connect() em vez de
    AsyncSessionLocal(): um AsyncSession normal, ligado ao Engine (não
    a uma Connection concreta), pode devolver a ligação física ao pool
    assim que uma transação termina (em cada `db.commit()`) e ir
    buscar OUTRA ligação física do pool na operação seguinte — o que já
    aconteceu na prática: um crud faz `db.add(x); await db.commit();
    await db.refresh(x)`, o commit devolve a ligação A ao pool, e o
    refresh a seguir apanha a ligação B (com app.current_tenant_id por
    definir, ou definido para outro tenant), e o Postgres recusa-se a
    "encontrar" a linha que acabou de ser criada — SQLAlchemy relata
    isto como "Could not refresh instance", nada a ver com um erro de
    SQL. `set_config(..., false)` (âmbito de sessão) só resolve isto se
    for a MESMA ligação física do início ao fim do pedido — daí fixar
    (`engine.connect()`) uma única Connection e vincular o Session a
    ela, em vez de deixar o Session gerir isso sozinho.

    ARMADILHA ADICIONAL (encontrada ao testar uma escola nova de raiz):
    o set_config TEM de ser executado ATRAVÉS da própria `sessao`
    (`sessao.execute(...)`), nunca através da `ligacao` crua antes de
    criar o Session. Se for executado na `ligacao` primeiro, isso
    despoleta o autobegin de uma transação "externa" ao Session; ao
    vincular um AsyncSession a uma Connection que já está em
    transação, o SQLAlchemy (join_transaction_mode="conditional_savepoint",
    o padrão) trata essa transação como não sendo dele — o
    `sessao.commit()` deixa de emitir COMMIT nenhum (confirmado via
    echo=True: nem COMMIT nem SAVEPOINT, silêncio total), e a
    transação fica pendurada até ao `ligacao.rollback()` da limpeza no
    `finally`, que desfaz a escrita inteira. Resultado: a API responde
    201 Created com um id válido (o id é gerado no lado do Python,
    `default=uuid.uuid4`, não por RETURNING), mas a linha nunca fica na
    base de dados — um bug silencioso, sem exceção nenhuma. Reproduzido
    e confirmado a criar um segundo Curso para uma escola nova
    (o primeiro tinha "sobrevivido" porque na altura ainda não se
    tinha percebido isto). Fazer o set_config through `sessao.execute`
    faz o autobegin ser do próprio Session, e `sessao.commit()` volta a
    emitir um COMMIT real.
    """
    tenant_str = str(utilizador["tenant_id"])
    async with engine.connect() as ligacao:
        async with AsyncSession(bind=ligacao, expire_on_commit=False) as sessao:
            try:
                # EXECUÇÃO CRÍTICA: injeta o tenant_id nesta ligação física
                # em concreto, através da própria sessao (ver docstring
                # acima — nunca através da `ligacao` crua). Nota: "SET
                # LOCAL x = :param" NÃO é válido em Postgres — SET/SET
                # LOCAL não aceitam parâmetros vinculados ($1), só
                # literais, o que dava sempre "syntax error at or near
                # '$1'". set_config() é a forma correta de definir uma GUC
                # parametrizada.
                await sessao.execute(
                    text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
                    {"tenant_id": tenant_str}
                )
                yield sessao
            finally:
                try:
                    await sessao.close()
                except Exception:
                    pass
                try:
                    # Se o pedido acabou por uma exceção a meio de uma
                    # transação, a ligação pode estar "abortada"
                    # (Postgres recusa qualquer comando até um
                    # ROLLBACK) — sem isto, a limpeza a seguir falhava
                    # sempre nesse caso.
                    await ligacao.rollback()
                    # Limpa antes de a ligação voltar ao pool — para o
                    # próximo pedido a reutilizar esta ligação física
                    # nunca herdar por engano o tenant_id deste pedido.
                    await ligacao.execute(text("SELECT set_config('app.current_tenant_id', '', false)"))
                except Exception:
                    pass  # a ligação vai de qualquer forma ser devolvida ao pool a seguir


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
