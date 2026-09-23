"""Ensaio geral (Dia 14 do PLANO_PRODUCAO.md) — percorre, por HTTP, o que uma
escola real faz do primeiro ao último dia útil, como uma escola nova:

  registo -> ativação -> configuração inicial -> curso/turma/disciplina/
  professor -> aluno + responsável + acessos ao Portal -> matrícula ->
  contrato (faturas) -> notas e faltas -> Responsável vê a fatura e reporta
  a transferência -> Secretaria recebe a notificação (com o link certo),
  confirma o pagamento -> recibo em PDF -> cartão de acesso em PDF ->
  pedido de documento -> comunicado ao Responsável (notificação clicável).

Cada passo imprime PASSOU/FALHOU e o percurso continua sempre que possível,
para o relatório final listar TODOS os tropeços de uma vez.

Uso (contra um back-end sobre a base de dados de TESTE, ex. porta 8001 — ver
scripts/teste_fumo_volume.py para o arranque):
    python scripts/ensaio_geral.py --base-url http://127.0.0.1:8001

O e-mail de ativação de conta não é lido (sem SMTP em teste): o único passo
que não é HTTP é marcar o e-mail do Gestor como verificado diretamente na
base de dados de teste, o mesmo atalho que tests/conftest.py usa.
"""
import argparse
import asyncio
import os
import random
import string
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.test", override=True)
if "test" not in os.environ["DATABASE_URL"].rsplit("/", 1)[-1]:
    raise SystemExit("DATABASE_URL de .env.test não aponta para uma base de dados de teste — a recusar correr.")

import httpx

_resultados: list[tuple[str, bool, str]] = []


def _passo(nome: str, ok: bool, detalhe: str = "") -> bool:
    _resultados.append((nome, ok, detalhe))
    print(f"[{'PASSOU' if ok else 'FALHOU'}] {nome}" + (f" — {detalhe}" if detalhe and not ok else ""))
    return ok


def _json(r: httpx.Response):
    try:
        return r.json()
    except Exception:
        return {}


async def _ativar_email_na_bd(email: str) -> None:
    from sqlalchemy import update
    from app.database.models import Usuario
    from app.database.session import AsyncSessionLocalSistema
    async with AsyncSessionLocalSistema() as db:
        await db.execute(update(Usuario).where(Usuario.email == email).values(email_verificado=True))
        await db.commit()


async def correr(base_url: str) -> None:
    suf = "".join(random.choices(string.digits, k=8))
    ano = date.today().year
    senha = "SenhaTeste123!"
    email_gestor = f"gestor.ensaio.{suf}@teste.pt"
    email_resp = f"resp.ensaio.{suf}@teste.pt"
    email_aluno = f"aluno.ensaio.{suf}@teste.pt"

    async with httpx.AsyncClient(base_url=base_url, timeout=60) as c:
        # 1. Registo + ativação + login
        r = await c.post("/api/v1/auth/registo", json={
            "nome_fantasia": f"Escola Ensaio {suf}", "nif": suf, "nome_gestor": "Gestor do Ensaio",
            "email_gestor": email_gestor, "palavra_passe": senha})
        _passo("Registo da escola (auto-serviço)", r.status_code == 201, r.text)
        r = await c.post("/api/v1/auth/login", data={"username": email_gestor, "password": senha})
        _passo("Login recusado até ativar o e-mail", r.status_code in (401, 403), f"veio {r.status_code}")
        await _ativar_email_na_bd(email_gestor)
        r = await c.post("/api/v1/auth/login", data={"username": email_gestor, "password": senha})
        if not _passo("Login do Gestor depois de ativar", r.status_code == 200, r.text):
            return
        h = {"Authorization": f"Bearer {_json(r)['access_token']}"}

        # 2. Configuração inicial (ano letivo, IBAN, moeda)
        r = await c.put("/api/v1/configuracoes", headers=h, json={
            "iban": "AO06004000001234567890123", "moeda": "AOA", "nota_maxima": 20, "nota_minima_aprovacao": 10,
            "data_inicio_ano_letivo": f"{ano}-01-15", "data_fim_ano_letivo": f"{ano}-12-15", "ano_letivo_atual": f"{ano}/{ano + 1}"})
        _passo("Configuração inicial (ano letivo, IBAN, moeda AOA)", r.status_code == 200, r.text)

        # 3. Estrutura académica
        curso = _json(await c.post("/api/v1/academico/cursos", headers=h, json={"nome": "Ensino Secundário"})).get("id")
        serie = _json(await c.post("/api/v1/academico/series", headers=h, json={"curso_id": curso, "nome": "10ª Classe"})).get("id")
        turma = _json(await c.post("/api/v1/academico/turmas", headers=h, json={
            "serie_ano_id": serie, "nome_codigo": "10ª A", "ano_letivo": ano, "vagas_maximas": 30})).get("id")
        disciplina = _json(await c.post("/api/v1/academico/disciplinas", headers=h, json={"nome": "Matemática", "carga_horaria_total": 4})).get("id")
        _passo("Curso, série, turma e disciplina", all([curso, serie, turma, disciplina]))
        prof = _json(await c.post("/api/v1/professores", headers=h, json={
            "nome_completo": "Prof Ensaio", "email": f"prof.ensaio.{suf}@teste.pt", "palavra_passe": senha})).get("id")
        r = await c.post(f"/api/v1/professores/{prof}/alocacoes", headers=h, json={"turma_id": turma, "disciplina_id": disciplina})
        _passo("Professor criado e alocado à turma/disciplina", r.status_code == 201, r.text)

        # 4. Aluno, responsável, acessos ao Portal, matrícula, contrato
        aluno = _json(await c.post("/api/v1/alunos", headers=h, json={
            "matricula_interna": f"E{suf}", "nome_completo": "Aluno do Ensaio", "data_nascimento": "2010-05-10"})).get("id")
        resp_id = _json(await c.post("/api/v1/responsaveis", headers=h, json={
            "nome_completo": "Encarregado do Ensaio", "telefone_contato": "+244900000000", "email": email_resp})).get("id")
        r = await c.post(f"/api/v1/alunos/{aluno}/responsaveis", headers=h, json={
            "responsavel_id": resp_id, "tipo_parentesco": "Mãe", "responsavel_financeiro": True})
        _passo("Aluno e Responsável criados e vinculados", bool(aluno and resp_id) and r.status_code == 201, r.text)
        r1 = await c.post(f"/api/v1/alunos/{aluno}/criar-acesso", headers=h, json={"email": email_aluno, "palavra_passe": senha})
        r2 = await c.post(f"/api/v1/responsaveis/{resp_id}/criar-acesso", headers=h, json={"email": email_resp, "palavra_passe": senha})
        _passo("Acessos ao Portal (aluno e responsável)", r1.status_code == 201 and r2.status_code == 201, f"{r1.text} {r2.text}")
        r = await c.post("/api/v1/matriculas", headers=h, json={"aluno_id": aluno, "turma_id": turma, "ano_letivo": ano})
        matricula = _json(r).get("id")
        _passo("Matrícula", r.status_code == 201, r.text)
        r = await c.post("/api/v1/financeiro/contratos", headers=h, json={
            "matricula_id": matricula, "responsavel_id": resp_id, "valor_total_anual": "120000.00", "quantidade_parcelas": 12})
        contrato = _json(r).get("id")
        faturas = _json(await c.get(f"/api/v1/financeiro/contratos/{contrato}/faturas", headers=h)) if contrato else []
        _passo("Contrato e 12 faturas geradas", r.status_code == 201 and len(faturas) == 12, f"{len(faturas)} faturas")

        # 5. Notas e faltas
        av = _json(await c.post(f"/api/v1/diario/turmas/{turma}/disciplinas/{disciplina}/avaliacoes", headers=h, json={
            "periodo_avaliacao": "1º Trimestre", "titulo": "Prova 1", "tipo_avaliacao": "CONTINUA", "peso": "100"})).get("id")
        r = await c.post(f"/api/v1/diario/avaliacoes/{av}/notas/lote", headers=h, json={"notas": [{"matricula_id": matricula, "valor_nota": "15.00"}]})
        _passo("Lançamento de nota", r.status_code == 200, r.text)
        r = await c.post(f"/api/v1/diario/turmas/{turma}/disciplinas/{disciplina}/frequencias/lote", headers=h, json={
            "data_aula": (date.today() - timedelta(days=1)).isoformat(), "quantidade_aulas": 1,
            "frequencias": [{"matricula_id": matricula, "presenca": False, "faltas": 1}]})
        _passo("Lançamento de faltas", r.status_code == 201, r.text)

        # 6. Portal do Responsável: vê a pauta e a fatura, reporta a transferência
        r = await c.post("/api/v1/auth/login", data={"username": email_resp, "password": senha})
        if _passo("Login do Responsável", r.status_code == 200, r.text):
            hr = {"Authorization": f"Bearer {_json(r)['access_token']}"}
            r = await c.get(f"/api/v1/portal/educandos/{aluno}/pauta", headers=hr)
            pauta = _json(r).get("disciplinas", [])
            _passo("Portal: pauta mostra a nota lançada", r.status_code == 200 and any(d.get("periodos") for d in pauta), r.text[:200])
            r = await c.get(f"/api/v1/portal/educandos/{aluno}/financeiro", headers=hr)
            fat = _json(r).get("faturas", [])
            _passo("Portal: fatura do Responsável visível", r.status_code == 200 and len(fat) == 12, f"{len(fat)} faturas")
            fatura_id = fat[0]["id"] if fat else None
            r = await c.patch(f"/api/v1/financeiro/faturas/{fatura_id}/reportar-pagamento", headers=hr, json={"referencia": "TRF-ENSAIO-001"})
            _passo("Responsável reporta a transferência", r.status_code == 200, r.text)

            # 7. Secretaria: notificação com o link certo, confirma e emite recibo
            r = await c.get("/api/v1/notificacoes", headers=h)
            itens = _json(r) if r.status_code == 200 and isinstance(_json(r), list) else []
            n = next((x for x in itens if "Pagamento reportado" in (x.get("titulo") or "")), None)
            _passo("Notificação de pagamento reportado chega ao Gestor", n is not None, str(itens)[:200])
            _passo("… e leva a /financeiro", bool(n) and n.get("link") == "/financeiro", str(n))
            r = await c.patch(f"/api/v1/financeiro/faturas/{fatura_id}/marcar-pago", headers=h, json={"forma_pagamento": "TRANSFERENCIA"})
            _passo("Secretaria confirma o pagamento (marcar pago)", r.status_code == 200, r.text)
            r = await c.get(f"/api/v1/financeiro/faturas/{fatura_id}/recibo", headers=h)
            _passo("Recibo em PDF", r.status_code == 200 and r.content[:4] == b"%PDF", f"{r.status_code} {r.content[:20]!r}")

            # 8. Cartão de acesso e pedido de documento
            r = await c.get(f"/api/v1/alunos/{aluno}/cartao-acesso.pdf", headers=h)
            _passo("Cartão de acesso em PDF", r.status_code == 200 and r.content[:4] == b"%PDF", f"{r.status_code}")
            await c.put("/api/v1/documentos/precos/DECLARACAO", headers=h, json={"preco": "1000.00", "ativo": True})
            r = await c.post("/api/v1/documentos/solicitacoes", headers=hr, json={"tipo_documento": "DECLARACAO", "formato_entrega": "DIGITAL"})
            _passo("Responsável pede uma Declaração", r.status_code in (200, 201), r.text)
            solic = _json(r).get("id")
            r = await c.get(f"/api/v1/documentos/solicitacoes/{solic}/pdf", headers=h)
            _passo("Declaração só sai depois de paga (sem pagamento devolve erro claro)", r.status_code in (400, 402, 403, 409), f"veio {r.status_code}")
            r = await c.patch(f"/api/v1/documentos/solicitacoes/{solic}/marcar-pago", headers=h)
            _passo("Secretaria confirma a transferência do pedido de documento", r.status_code == 200, r.text)
            r = await c.get(f"/api/v1/documentos/solicitacoes/{solic}/pdf", headers=hr)
            _passo("Responsável descarrega a Declaração em PDF", r.status_code == 200 and r.content[:4] == b"%PDF", f"{r.status_code}")

            # 9. Comunicado com notificação clicável no Portal
            r = await c.post("/api/v1/comunicados", headers=h, json={
                "tipo": "COMUNICADO", "titulo": "Reunião de pais", "corpo": "Sexta-feira às 17h.",
                "destinatario_tipo": "TURMA", "destinatario_turma_id": turma})
            _passo("Comunicado enviado à turma", r.status_code == 201, r.text)
            r = await c.get("/api/v1/notificacoes", headers=hr)
            itens = _json(r) if r.status_code == 200 and isinstance(_json(r), list) else []
            n = next((x for x in itens if x.get("tipo") == "COMUNICADO"), None)
            _passo("Notificação do comunicado chega ao Responsável, a levar a /portal?tab=comunicados", bool(n) and n.get("link") == "/portal?tab=comunicados", str(itens)[:200])

    falhas = [x for x in _resultados if not x[1]]
    print(f"\n{len(_resultados) - len(falhas)}/{len(_resultados)} passos OK.")
    for nome, _, detalhe in falhas:
        print(f"  FALHOU: {nome} — {detalhe[:300]}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://127.0.0.1:8001")
    asyncio.run(correr(p.parse_args().base_url))
