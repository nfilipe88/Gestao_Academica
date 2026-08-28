"""
Teste de carga (Fase 6 — escala): mede o comportamento real da API sob
concorrência, para dar números concretos em vez de "deve ficar mais
rápido" — em particular, valida o sizing do pool de ligações
(app/database/session.py::DB_POOL_SIZE/DB_POOL_MAX_OVERFLOW).

O QUE ISTO NÃO É: um benchmark "antes/depois" dos índices em tenant_id
(migração cde309e6fb09). Isso exigiria uma base de dados do tamanho de
produção real (milhares de escolas, milhões de linhas) — numa base de
dados pequena (a de desenvolvimento, ou até uma de testes populada a
propósito), um sequential scan já é rápido de qualquer forma, com ou
sem índice, e o teste não mostraria diferença nenhuma. O valor dos
índices não é "mais rápido hoje", é "continua rápido quando a tabela
tiver 2 milhões de linhas em vez de 200" — isso prova-se pelo plano de
execução (EXPLAIN ANALYZE), não por um cronómetro numa BD pequena.

O QUE ISTO É: dispara um volume real de pedidos concorrentes contra a
API já a correr (localhost:8000 por omissão) e mede taxa de sucesso,
throughput e latência (p50/p95/p99). Antes da Fase 6, o pool de
ligações ficava no valor por omissão do SQLAlchemy (pool_size=5 +
max_overflow=10 = 15 ligações no total) — com mais concorrência do que
isso, os pedidos a mais ficam à espera de uma ligação livre (mais
lentos) ou falham de vez com QueuePool timeout. Este script confirma
que, com o sizing atual (pool_size=20 + max_overflow=20 = 40 por
omissão), a API aguenta um volume de pedidos em paralelo maior do que
o pool antigo sem erros nem degradação severa.

Uso:
    python scripts/teste_carga.py                          # contra localhost:8000
    python scripts/teste_carga.py --base-url http://... --concorrencia 60 --pedidos 300
"""
import argparse
import asyncio
import random
import statistics
import string
import time

import httpx


def _sufixo(tamanho: int = 8) -> str:
    return "".join(random.choices(string.digits, k=tamanho))


async def _preparar_escola(client: httpx.AsyncClient) -> dict:
    """Regista uma escola nova de propósito para o teste (auto-serviço,
    o mesmo caminho que uma escola real usaria) e devolve um token
    válido — o teste de carga nunca deve mexer em dados reais."""
    suf = _sufixo()
    email = f"gestor.carga.{suf}@teste.pt"
    senha = "SenhaTeste123!"
    resp = await client.post("/api/v1/auth/registo", json={
        "nome_fantasia": f"Escola Teste de Carga {suf}", "nif": suf,
        "nome_gestor": "Gestor Teste de Carga", "email_gestor": email, "palavra_passe": senha,
    })
    resp.raise_for_status()
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
    resp.raise_for_status()
    return resp.json()


async def _popular_dados_minimos(client: httpx.AsyncClient, headers: dict) -> None:
    """Uns poucos registos, só para os GETs abaixo terem alguma coisa
    real para listar (não é o volume que importa aqui, é a concorrência)."""
    resp = await client.post("/api/v1/academico/cursos", json={"nome": "Ensino Primário"}, headers=headers)
    curso_id = resp.json()["id"]
    await client.post("/api/v1/academico/series", json={"curso_id": curso_id, "nome": "1ª Classe"}, headers=headers)
    for i in range(5):
        await client.post("/api/v1/alunos", json={
            "matricula_interna": f"AL{_sufixo()}", "nome_completo": f"Aluno Carga {i}", "data_nascimento": "2015-01-01",
        }, headers=headers)


async def _um_pedido(client: httpx.AsyncClient, headers: dict, endpoint: str) -> tuple[bool, float]:
    inicio = time.perf_counter()
    try:
        resp = await client.get(endpoint, headers=headers)
        ok = resp.status_code == 200
    except Exception:
        ok = False
    duracao = time.perf_counter() - inicio
    return ok, duracao


def _percentil(valores: list[float], p: float) -> float:
    valores_ordenados = sorted(valores)
    k = int(len(valores_ordenados) * p)
    return valores_ordenados[min(k, len(valores_ordenados) - 1)]


async def correr(base_url: str, concorrencia: int, total_pedidos: int) -> None:
    endpoints = ["/api/v1/alunos?page=1&page_size=10", "/api/v1/academico/cursos", "/api/v1/notificacoes/contagem", "/api/v1/configuracoes"]

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        print(f"A preparar uma escola de teste em {base_url}...")
        sessao = await _preparar_escola(client)
        headers = {"Authorization": f"Bearer {sessao['access_token']}"}
        await _popular_dados_minimos(client, headers)

        print(f"A disparar {total_pedidos} pedidos com concorrência {concorrencia} (pool: ver DB_POOL_SIZE/DB_POOL_MAX_OVERFLOW no .env)...")
        semaforo = asyncio.Semaphore(concorrencia)

        async def _tarefa(i: int):
            async with semaforo:
                return await _um_pedido(client, headers, endpoints[i % len(endpoints)])

        inicio_total = time.perf_counter()
        resultados = await asyncio.gather(*[_tarefa(i) for i in range(total_pedidos)])
        duracao_total = time.perf_counter() - inicio_total

    sucessos = [d for ok, d in resultados if ok]
    falhas = total_pedidos - len(sucessos)
    duracoes_ms = [d * 1000 for d in sucessos]

    print()
    print("=" * 60)
    print(f"Pedidos totais:        {total_pedidos}")
    print(f"Concorrência:          {concorrencia}")
    print(f"Sucesso:               {len(sucessos)} ({100 * len(sucessos) / total_pedidos:.1f}%)")
    print(f"Falhas:                {falhas}")
    print(f"Duração total:         {duracao_total:.2f}s")
    print(f"Throughput:            {total_pedidos / duracao_total:.1f} pedidos/s")
    if duracoes_ms:
        print(f"Latência média:        {statistics.mean(duracoes_ms):.1f} ms")
        print(f"Latência p50:          {_percentil(duracoes_ms, 0.50):.1f} ms")
        print(f"Latência p95:          {_percentil(duracoes_ms, 0.95):.1f} ms")
        print(f"Latência p99:          {_percentil(duracoes_ms, 0.99):.1f} ms")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concorrencia", type=int, default=60, help="Pedidos em paralelo (> 15, o antigo limite do pool, de propósito)")
    parser.add_argument("--pedidos", type=int, default=300, help="Total de pedidos a disparar")
    args = parser.parse_args()

    asyncio.run(correr(args.base_url, args.concorrencia, args.pedidos))
