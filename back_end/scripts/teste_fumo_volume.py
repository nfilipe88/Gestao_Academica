"""Teste de fumo com volume realista (Dia 12 do PLANO_PRODUCAO.md) — NÃO é
um teste de carga (isso é scripts/teste_carga.py, foca a concorrência):
aqui o que interessa é o VOLUME de dados. Popula a base de dados de TESTE
com um número de escolas/turmas/alunos/faturas/notas parecido com o que as
10 escolas de teste vão gerar, e mede os tempos de resposta dos ecrãs que
mais dados agregam (Diário, Pauta, Indicadores, Estatísticas, Financeiro).

Duas fases, sempre contra a base de dados de teste (o script recusa correr
se DATABASE_URL de .env.test não tiver "test" no nome):

  1. semear — em processo (ASGI, sem servidor), escreve na academic_db_test
     e guarda IDs/credenciais num JSON:
         python scripts/teste_fumo_volume.py semear --saida fumo.json
  2. medir — por HTTP, contra um back-end JÁ a correr sobre a mesma base
     de dados de teste (ver README/RUNBOOK: arrancar uvicorn com o ambiente
     de .env.test, ex. na porta 8001):
         python scripts/teste_fumo_volume.py medir --entrada fumo.json --base-url http://127.0.0.1:8001
"""
import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.test", override=True)
if "test" not in os.environ["DATABASE_URL"].rsplit("/", 1)[-1]:
    raise SystemExit("DATABASE_URL de .env.test não aponta para uma base de dados de teste — a recusar correr.")

import httpx


async def _semear(args) -> None:
    from httpx import ASGITransport, AsyncClient
    from main import app
    from app.core import rate_limiter
    from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico

    ano = date.today().year
    resultado = {"ano_letivo": ano, "escolas": []}
    disciplinas_nomes = ["Matemática", "Português", "Física", "Química", "Biologia", "História", "Geografia", "Inglês"][:args.disciplinas]
    periodos = ["1º Trimestre", "2º Trimestre", "3º Trimestre"]
    inicio_total = time.perf_counter()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste.local", timeout=120) as client:
        for n in range(args.escolas):
            rate_limiter._memoria.clear()  # 5 registos/hora por IP — o semeador é um único "IP"
            t0 = time.perf_counter()
            escola = await criar_escola_e_gestor(client, f"fumo{n}")
            h = auth_headers(escola["token"])

            curso = (await client.post("/api/v1/academico/cursos", json={"nome": "Ensino Secundário"}, headers=h)).json()["id"]
            serie = (await client.post("/api/v1/academico/series", json={"curso_id": curso, "nome": "10ª Classe"}, headers=h)).json()["id"]
            disciplinas = []
            for nome in disciplinas_nomes:
                r = await client.post("/api/v1/academico/disciplinas", json={"nome": nome, "carga_horaria_total": 4}, headers=h)
                disciplinas.append(r.json()["id"])
            r = await client.post("/api/v1/professores", headers=h, json={
                "nome_completo": "Prof Fumo", "email": f"prof.fumo.{sufixo_unico()}@teste.pt", "palavra_passe": "SenhaTeste123!"})
            professor = r.json()["id"]

            turmas = []
            for t in range(args.turmas):
                r = await client.post("/api/v1/academico/turmas", headers=h, json={
                    "serie_ano_id": serie, "nome_codigo": f"10ª {chr(65 + t)}", "ano_letivo": ano, "vagas_maximas": args.alunos_por_turma + 5})
                turma_id = r.json()["id"]
                for d in disciplinas:
                    await client.post(f"/api/v1/professores/{professor}/alocacoes", headers=h, json={"turma_id": turma_id, "disciplina_id": d})

                sem = asyncio.Semaphore(6)
                matriculas: list[str] = []
                primeiro: dict = {}

                async def _aluno(i: int):
                    async with sem:
                        suf = sufixo_unico(10)
                        a = (await client.post("/api/v1/alunos", headers=h, json={
                            "matricula_interna": f"F{suf}", "nome_completo": f"Aluno Fumo {n}-{t}-{i}", "data_nascimento": "2010-03-15"})).json()["id"]
                        rsp = (await client.post("/api/v1/responsaveis", headers=h, json={
                            "nome_completo": f"Responsável {n}-{t}-{i}", "telefone_contato": "+244900000000"})).json()["id"]
                        await client.post(f"/api/v1/alunos/{a}/responsaveis", headers=h, json={
                            "responsavel_id": rsp, "tipo_parentesco": "Mãe", "responsavel_financeiro": True})
                        m = (await client.post("/api/v1/matriculas", headers=h, json={"aluno_id": a, "turma_id": turma_id, "ano_letivo": ano})).json()["id"]
                        r_ct = await client.post("/api/v1/financeiro/contratos", headers=h, json={
                            "matricula_id": m, "responsavel_id": rsp, "valor_total_anual": "1200.00", "quantidade_parcelas": 12})
                        assert r_ct.status_code == 201, r_ct.text
                        matriculas.append(m)
                        if i == 0:
                            primeiro.update(aluno_id=a, responsavel_id=rsp, contrato_id=r_ct.json()["id"])

                await asyncio.gather(*[_aluno(i) for i in range(args.alunos_por_turma)])

                for d in disciplinas:
                    for periodo in periodos:
                        for k in range(args.avaliacoes_por_periodo):
                            av = (await client.post(f"/api/v1/diario/turmas/{turma_id}/disciplinas/{d}/avaliacoes", headers=h, json={
                                "periodo_avaliacao": periodo, "titulo": f"Prova {k + 1}", "tipo_avaliacao": "CONTINUA", "peso": "100"})).json()["id"]
                            notas = [{"matricula_id": m, "valor_nota": str(4 + (hash((m, k, periodo)) % 60) / 10)} for m in matriculas]
                            r = await client.post(f"/api/v1/diario/avaliacoes/{av}/notas/lote", headers=h, json={"notas": notas})
                            assert r.status_code == 200, r.text
                    for dia in range(args.aulas_por_disciplina):
                        await client.post(f"/api/v1/diario/turmas/{turma_id}/disciplinas/{d}/frequencias/lote", headers=h, json={
                            "data_aula": (date.today() - timedelta(days=dia + 1)).isoformat(), "quantidade_aulas": 1,
                            "frequencias": [{"matricula_id": m, "presenca": (hash((m, dia)) % 10) != 0, "faltas": 0 if (hash((m, dia)) % 10) else 1} for m in matriculas]})

                turmas.append({"turma_id": turma_id, "disciplina_id": disciplinas[0], **primeiro})

            # Credenciais de um Responsável do Portal (para medir a Pauta/Boletim/Financeiro dele)
            primeiro = turmas[0]
            email_resp = f"resp.fumo.{sufixo_unico()}@teste.pt"
            r = await client.post(f"/api/v1/responsaveis/{primeiro['responsavel_id']}/criar-acesso", headers=h, json={"email": email_resp, "palavra_passe": "SenhaTeste123!"})
            assert r.status_code == 201, r.text

            resultado["escolas"].append({
                "gestor_email": escola["email"], "gestor_senha": escola["senha"], "turmas": turmas,
                "responsavel_email": email_resp, "responsavel_senha": "SenhaTeste123!", "aluno_id": primeiro["aluno_id"],
            })
            print(f"escola {n + 1}/{args.escolas} semeada em {time.perf_counter() - t0:.0f}s")

    Path(args.saida).write_text(json.dumps(resultado, indent=1), encoding="utf-8")
    total_alunos = args.escolas * args.turmas * args.alunos_por_turma
    print(f"\nSemeado: {args.escolas} escolas, {total_alunos} alunos, {total_alunos * 12} faturas, "
          f"{args.escolas * args.turmas * len(disciplinas_nomes) * 3 * args.avaliacoes_por_periodo * args.alunos_por_turma} notas "
          f"em {time.perf_counter() - inicio_total:.0f}s. Credenciais/IDs em {args.saida}.")


async def _medir(args) -> None:
    dados = json.loads(Path(args.entrada).read_text(encoding="utf-8"))
    ano = dados["ano_letivo"]

    async def _login(client, email, senha):
        r = await client.post("/api/v1/auth/login", data={"username": email, "password": senha})
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    linhas = []
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120) as client:
        escola = dados["escolas"][0]
        h = await _login(client, escola["gestor_email"], escola["gestor_senha"])
        hr = await _login(client, escola["responsavel_email"], escola["responsavel_senha"])
        t = escola["turmas"][0]

        gestor = {
            "Alunos (lista, 100)": "/api/v1/alunos?page_size=100",
            "Turmas": "/api/v1/academico/turmas",
            "Diário — consolidado da turma": f"/api/v1/diario/turmas/{t['turma_id']}/disciplinas/{t['disciplina_id']}/consolidado",
            "Diário — notas finais": f"/api/v1/diario/turmas/{t['turma_id']}/disciplinas/{t['disciplina_id']}/notas-finais?periodo_avaliacao=1º Trimestre",
            "Indicadores": "/api/v1/indicadores",
            "Indicadores — risco de evasão": "/api/v1/indicadores/risco-evasao",
            "Estatísticas — dashboard": "/api/v1/estatisticas/dashboard",
            "Financeiro — faturas de um contrato": f"/api/v1/financeiro/contratos/{t['contrato_id']}/faturas",
            "Relatório de Indicadores (PDF)": "/api/v1/indicadores/relatorio.pdf",
            "Estatísticas — relatório do ano": f"/api/v1/estatisticas/relatorio?data_inicio={ano}-01-01&data_fim={ano}-12-31",
            "Estatísticas — relatório .xlsx": f"/api/v1/estatisticas/relatorio.xlsx?data_inicio={ano}-01-01&data_fim={ano}-12-31",
        }
        portal = {
            "Portal — meus educandos": "/api/v1/portal/meus-educandos",
            f"Portal — pauta": f"/api/v1/portal/educandos/{escola['aluno_id']}/pauta",
            "Portal — boletim": f"/api/v1/portal/educandos/{escola['aluno_id']}/boletim",
            "Portal — financeiro": f"/api/v1/portal/educandos/{escola['aluno_id']}/financeiro",
            "Portal — estatísticas": f"/api/v1/portal/educandos/{escola['aluno_id']}/estatisticas",
        }
        for nome, url, cab in [(n, u, h) for n, u in gestor.items()] + [(n, u, hr) for n, u in portal.items()]:
            tempos, estado = [], set()
            for _ in range(args.repeticoes):
                t0 = time.perf_counter()
                r = await client.get(url, headers=cab)
                tempos.append((time.perf_counter() - t0) * 1000)
                estado.add(r.status_code)
            tempos.sort()
            linhas.append((nome, min(estado), statistics.median(tempos), tempos[int(len(tempos) * 0.95) - 1] if len(tempos) > 1 else tempos[0], len(r.content)))

        # Concorrência realista: gestores de escolas diferentes a abrir o dashboard ao mesmo tempo
        hs = [await _login(client, e["gestor_email"], e["gestor_senha"]) for e in dados["escolas"]]
        t0 = time.perf_counter()
        respostas = await asyncio.gather(*[client.get("/api/v1/estatisticas/dashboard", headers=x) for x in hs for _ in range(3)])
        conc = (time.perf_counter() - t0) * 1000
        erros = sum(1 for r in respostas if r.status_code != 200)

    print(f"{'Ecrã / endpoint':<40}{'HTTP':>6}{'mediana ms':>12}{'p95 ms':>10}{'bytes':>10}")
    for nome, st, med, p95, tam in linhas:
        aviso = "  <-- LENTO" if med > args.limite_ms else ""
        print(f"{nome:<40}{st:>6}{med:>12.0f}{p95:>10.0f}{tam:>10}{aviso}")
    print(f"\nConcorrência: {len(respostas)} dashboards de {len(hs)} escolas em paralelo — {conc:.0f} ms no total, {erros} erro(s).")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("semear")
    s.add_argument("--saida", default="fumo.json")
    s.add_argument("--escolas", type=int, default=10)
    s.add_argument("--turmas", type=int, default=6)
    s.add_argument("--alunos-por-turma", type=int, default=30)
    s.add_argument("--disciplinas", type=int, default=8)
    s.add_argument("--avaliacoes-por-periodo", type=int, default=2)
    s.add_argument("--aulas-por-disciplina", type=int, default=20)
    m = sub.add_parser("medir")
    m.add_argument("--entrada", default="fumo.json")
    m.add_argument("--base-url", default="http://127.0.0.1:8001")
    m.add_argument("--repeticoes", type=int, default=5)
    m.add_argument("--limite-ms", type=int, default=1500, help="Acima disto (mediana) o ecrã é assinalado como lento")
    args = p.parse_args()
    asyncio.run(_semear(args) if args.cmd == "semear" else _medir(args))


if __name__ == "__main__":
    main()
