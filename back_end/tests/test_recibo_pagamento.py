"""Recibo de pagamento + moeda AOA (Fase 3 — Angola) — ponta a ponta:
uma escola configurada em Kwanza não pode gerar cobrança PayPal (o
PayPal não aceita AOA), mas o pagamento manual continua a funcionar e
emite um recibo em PDF com numeração sequencial correta."""
from datetime import date, timedelta

from tests.conftest import auth_headers, criar_escola_e_gestor, sufixo_unico


async def _preparar_contrato_com_2_parcelas(client, headers, ano_letivo: int) -> list[dict]:
    resp = await client.post("/api/v1/academico/cursos", json={"nome": "Ensino Primário"}, headers=headers)
    curso_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/academico/series", json={"curso_id": curso_id, "nome": "1ª Classe"}, headers=headers
    )
    serie_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/academico/turmas",
        json={"serie_ano_id": serie_id, "nome_codigo": "1A", "ano_letivo": ano_letivo, "vagas_maximas": 30},
        headers=headers,
    )
    turma_id = resp.json()["id"]

    suf = sufixo_unico()
    resp = await client.post(
        "/api/v1/alunos",
        json={"matricula_interna": f"AL{suf}", "nome_completo": "Aluno Recibo", "data_nascimento": "2015-01-01"},
        headers=headers,
    )
    aluno_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/responsaveis",
        json={"nome_completo": "Encarregado Recibo", "telefone_contato": "+244923000000", "numero_documento": "001234567LA042"},
        headers=headers,
    )
    responsavel_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/responsaveis",
        json={"responsavel_id": responsavel_id, "tipo_parentesco": "Pai", "responsavel_financeiro": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        "/api/v1/matriculas",
        json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": ano_letivo},
        headers=headers,
    )
    matricula_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/financeiro/contratos",
        json={
            "matricula_id": matricula_id, "responsavel_id": responsavel_id,
            "valor_total_anual": "120000.00", "quantidade_parcelas": 2,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    contrato_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/financeiro/contratos/{contrato_id}/faturas", headers=headers)
    return resp.json()


async def test_escola_em_aoa_nao_pode_gerar_cobranca_paypal(client):
    escola = await criar_escola_e_gestor(client, "aoa")
    headers = auth_headers(escola["token"])

    resp = await client.put("/api/v1/configuracoes", json={"moeda": "AOA", "nota_maxima": 10}, headers=headers)
    assert resp.status_code == 200 and resp.json()["moeda"] == "AOA"

    faturas = await _preparar_contrato_com_2_parcelas(client, headers, date.today().year)
    fatura_id = faturas[0]["id"]

    resp = await client.post(
        f"/api/v1/financeiro/faturas/{fatura_id}/gerar-cobranca", json={"metodo_pagamento": "PAYPAL"}, headers=headers
    )
    assert resp.status_code == 400
    assert "AOA" in resp.json()["detail"] and "PayPal" in resp.json()["detail"]


async def test_recibo_emitido_ao_marcar_pago_com_numeracao_sequencial(client):
    escola = await criar_escola_e_gestor(client, "recibo")
    headers = auth_headers(escola["token"])
    await client.put("/api/v1/configuracoes", json={"moeda": "AOA", "nota_maxima": 10}, headers=headers)

    faturas = await _preparar_contrato_com_2_parcelas(client, headers, date.today().year)
    fatura1_id, fatura2_id = faturas[0]["id"], faturas[1]["id"]

    # Antes de paga, não há recibo nenhum.
    resp = await client.get(f"/api/v1/financeiro/faturas/{fatura1_id}/recibo", headers=headers)
    assert resp.status_code == 404

    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura1_id}/marcar-pago", json={"forma_pagamento": "MULTICAIXA"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/financeiro/faturas/{fatura1_id}/recibo", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF", "a resposta não parece um PDF válido"

    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura2_id}/marcar-pago", json={"forma_pagamento": "TRANSFERENCIA"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    resp = await client.get(f"/api/v1/financeiro/faturas/{fatura2_id}/recibo", headers=headers)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"

    # Pagar a mesma fatura outra vez tem de ser recusado (idempotência)
    # — sem isto, um duplo-clique podia emitir um segundo recibo com o
    # mesmo número já usado por outra escola/fatura no mesmo ano.
    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura1_id}/marcar-pago", json={"forma_pagamento": "MULTICAIXA"}, headers=headers
    )
    assert resp.status_code == 400


async def test_reportar_pagamento_fatura_transferencia(client):
    """Auto-relato ("já efetuei a transferência") — aditivo: não marca a
    fatura como paga, só regista o relato para a Secretaria confirmar
    depois via marcar-pago."""
    escola = await criar_escola_e_gestor(client, "reporte")
    headers = auth_headers(escola["token"])
    await client.put("/api/v1/configuracoes", json={"moeda": "AOA", "nota_maxima": 10}, headers=headers)

    faturas = await _preparar_contrato_com_2_parcelas(client, headers, date.today().year)
    fatura_id = faturas[0]["id"]

    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura_id}/reportar-pagamento",
        json={"referencia": "Transferência BAI, 19/09"}, headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["pagamento_reportado_em"] is not None

    resp = await client.get(f"/api/v1/financeiro/faturas/{fatura_id}", headers=headers)
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["status_pagamento"] == "PENDENTE"  # nunca marca como paga sozinho
    assert dados["pagamento_reportado_em"] is not None
    assert dados["pagamento_reportado_referencia"] == "Transferência BAI, 19/09"

    # Já reportado, continua livre para a Secretaria confirmar normalmente.
    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura_id}/marcar-pago", json={"forma_pagamento": "TRANSFERENCIA"}, headers=headers
    )
    assert resp.status_code == 200, resp.text


async def test_reportar_pagamento_fatura_ja_paga_e_recusado(client):
    escola = await criar_escola_e_gestor(client, "reportepago")
    headers = auth_headers(escola["token"])
    await client.put("/api/v1/configuracoes", json={"moeda": "AOA", "nota_maxima": 10}, headers=headers)

    faturas = await _preparar_contrato_com_2_parcelas(client, headers, date.today().year)
    fatura_id = faturas[0]["id"]

    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura_id}/marcar-pago", json={"forma_pagamento": "MULTICAIXA"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    resp = await client.patch(
        f"/api/v1/financeiro/faturas/{fatura_id}/reportar-pagamento", json={}, headers=headers
    )
    assert resp.status_code == 400


async def test_regua_cobranca_ignora_fatura_ja_reportada(client):
    """RN04: uma fatura com o pagamento já reportado não deve gerar um
    novo lembrete de vencimento — seria estranho avisar de atraso logo
    a seguir ao Responsável dizer que já pagou (ver processar_regua_cobranca_do_tenant)."""
    escola = await criar_escola_e_gestor(client, "reguareporte")
    headers = auth_headers(escola["token"])
    await client.put("/api/v1/configuracoes", json={"moeda": "AOA", "nota_maxima": 10}, headers=headers)

    hoje = date.today()
    # dia_vencimento_padrao só aceita 1-28; força a 1ª parcela a vencer
    # hoje (dias_para_vencer == 0), o gatilho mais simples de reproduzir
    # sem esperar dias reais.
    dia = min(hoje.day, 28)
    resp = await client.post("/api/v1/academico/cursos", json={"nome": "Ensino Primário"}, headers=headers)
    curso_id = resp.json()["id"]
    resp = await client.post("/api/v1/academico/series", json={"curso_id": curso_id, "nome": "1ª Classe"}, headers=headers)
    serie_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/academico/turmas",
        json={"serie_ano_id": serie_id, "nome_codigo": "1A", "ano_letivo": hoje.year, "vagas_maximas": 30},
        headers=headers,
    )
    turma_id = resp.json()["id"]

    suf = sufixo_unico()
    resp = await client.post(
        "/api/v1/alunos",
        json={"matricula_interna": f"AL{suf}", "nome_completo": "Aluno Regua", "data_nascimento": "2015-01-01"},
        headers=headers,
    )
    aluno_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/responsaveis",
        json={"nome_completo": "Encarregado Regua", "email": f"regua{suf}@teste.pt", "telefone_contato": "+244923000000", "numero_documento": "001234567LA042"},
        headers=headers,
    )
    responsavel_id = resp.json()["id"]
    resp = await client.post(
        f"/api/v1/alunos/{aluno_id}/responsaveis",
        json={"responsavel_id": responsavel_id, "tipo_parentesco": "Pai", "responsavel_financeiro": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    resp = await client.post(
        "/api/v1/matriculas", json={"aluno_id": aluno_id, "turma_id": turma_id, "ano_letivo": hoje.year}, headers=headers
    )
    matricula_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/financeiro/contratos",
        json={
            "matricula_id": matricula_id, "responsavel_id": responsavel_id,
            "valor_total_anual": "120000.00", "quantidade_parcelas": 2,
            "dia_vencimento_padrao": dia, "mes_primeira_parcela": hoje.month,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    contrato_id = resp.json()["id"]
    resp = await client.get(f"/api/v1/financeiro/contratos/{contrato_id}/faturas", headers=headers)
    fatura_id = resp.json()[0]["id"]
    assert resp.json()[0]["data_vencimento"] == hoje.isoformat()

    await client.patch(f"/api/v1/financeiro/faturas/{fatura_id}/reportar-pagamento", json={}, headers=headers)

    resp = await client.post("/api/v1/financeiro/regua-cobranca/processar", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["emails_enviados"]["lembrete_vencimento"] == 0
