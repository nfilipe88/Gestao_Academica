"""Configuração partilhada dos testes de integração.

IMPORTANTE: carrega back_end/.env.test ANTES de qualquer import de
app.* — app/database/session.py e app/core/security.py leem as
variáveis de ambiente (DATABASE_URL, DATABASE_URL_SISTEMA,
JWT_SECRET_KEY) no momento em que o módulo é importado, não a cada
pedido. Se isto corresse depois, os testes ligavam-se silenciosamente
à base de dados de desenvolvimento (a mesma usada manualmente durante
o desenvolvimento) em vez da academic_db_test isolada.

Pré-requisito único, local ou em CI: a base de dados de teste já tem
de existir com os grants dos roles app_tenant/app_sistema (ver
scripts/criar_db_teste.py) e as migrações aplicadas (`alembic upgrade
head` com DATABASE_URL_MIGRACOES a apontar para ela) — não é feito
aqui para os testes não pagarem esse custo a cada execução; ver
.github/workflows/ci.yml para a sequência completa em CI.
"""
import os
import random
import string
from pathlib import Path

from dotenv import load_dotenv

_ENV_TEST = Path(__file__).resolve().parent.parent / ".env.test"
if not _ENV_TEST.exists():
    raise RuntimeError(
        "back_end/.env.test não encontrado. Copie .env.test.example para "
        ".env.test e aponte para uma base de dados de teste (NUNCA a de "
        "desenvolvimento) — ver back_end/scripts/criar_db_teste.py."
    )
load_dotenv(_ENV_TEST, override=True)
if "_test" not in os.environ["DATABASE_URL"] and "test" not in os.environ["DATABASE_URL"].rsplit("/", 1)[-1]:
    raise RuntimeError(
        "DATABASE_URL em .env.test não parece apontar para uma base de "
        "dados de teste (o nome não contém 'test') — a correr os testes "
        "às cegas arriscava apagar/poluir dados reais. Revê .env.test."
    )

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    """Cliente HTTP assíncrono ligado diretamente à app ASGI — sem
    servidor a correr, mesma pilha de middlewares/dependências que um
    pedido real."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://teste.local") as ac:
        yield ac


def sufixo_unico(tamanho: int = 8) -> str:
    """Sufixo aleatório para nomes/NIFs/e-mails — os testes correm contra
    uma base de dados real e persistente entre execuções (não há reset
    automático), por isso nunca reutilizam um NIF/e-mail fixo."""
    return "".join(random.choices(string.digits, k=tamanho))


async def criar_escola_e_gestor(client: AsyncClient, prefixo: str = "teste") -> dict:
    """Regista uma escola nova (via auto-serviço, POST /auth/registo —
    o mesmo caminho que uma escola real usaria), depois faz login (o
    registo em si não devolve token nem ids — só confirmação) e devolve
    os dados úteis para os testes: token, ids, credenciais.
    """
    suf = sufixo_unico()
    nif = f"{suf}"
    # ".invalid" seria o domínio reservado "correto" para testes (RFC
    # 2606), mas o email-validator (usado pelo EmailStr) rejeita-o
    # explicitamente por ser special-use — daí "teste.pt", o mesmo
    # domínio já usado nos scripts manuais desta sessão.
    email = f"gestor.{prefixo}.{suf}@teste.pt"
    senha = "SenhaTeste123!"

    resp = await client.post("/api/v1/auth/registo", json={
        "nome_fantasia": f"Escola {prefixo} {suf}",
        "nif": nif,
        "nome_gestor": f"Gestor {prefixo}",
        "email_gestor": email,
        "palavra_passe": senha,
    })
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    corpo = resp.json()

    return {
        "nif": nif,
        "email": email,
        "senha": senha,
        "token": corpo["access_token"],
        "tenant_id": corpo["utilizador"]["tenant_id"],
        "usuario_id": corpo["utilizador"]["id"],
    }


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
