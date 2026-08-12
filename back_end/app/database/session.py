from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi import Depends
from app.core.security import obter_utilizador_atual
from typing import Dict, Any, AsyncGenerator
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Crie um ficheiro .env na raiz do back_end "
        "com base no .env.example."
    )

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def obter_sessao_db(
    utilizador: Dict[str, Any] = Depends(obter_utilizador_atual)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Injeta a sessão do banco de dados e configura a variável local do Postgres 
    para ativar o Row Level Security (RLS) automaticamente para o Tenant ativo.
    """
    async with AsyncSessionLocal() as sessao:
        # EXECUÇÃO CRÍTICA: Injeta o tenant_id na sessão atual do PostgreSQL
        # Nota: "SET LOCAL x = :param" NÃO é válido em Postgres — SET/SET
        # LOCAL não aceitam parâmetros vinculados ($1), só literais, o que
        # dava sempre "syntax error at or near '$1'" (500 em todos os
        # endpoints académicos). set_config() é a forma correta de definir
        # uma GUC parametrizada; o 3º argumento (true) replica o
        # comportamento de SET LOCAL (âmbito da transação atual).
        tenant_str = str(utilizador["tenant_id"])
        await sessao.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_str}
        )

        try:
            yield sessao
        finally:
            await sessao.close()


async def obter_sessao_db_publica() -> AsyncGenerator[AsyncSession, None]:
    """
    Sessão sem utilizador autenticado, para rotas verdadeiramente
    públicas (ex.: webhooks de gateways de pagamento — é o PayPal quem
    chama, não há um Bearer token nosso). Sem `obter_utilizador_atual`
    não há tenant_id para configurar `app.current_tenant_id`; quem
    chamar isto tem de descobrir o tenant a partir dos dados recebidos
    (ex.: TransacaoGateway.gateway_transaction_id) e filtrar
    explicitamente por ele nas queries seguintes — a mesma disciplina de
    "RLS + WHERE tenant_id=..." explícito usada em todo o resto da
    aplicação, só que aqui o tenant_id só é conhecido depois da
    primeira query.
    """
    async with AsyncSessionLocal() as sessao:
        try:
            yield sessao
        finally:
            await sessao.close()