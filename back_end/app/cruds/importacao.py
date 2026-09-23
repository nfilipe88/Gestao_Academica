"""
Importação de Dados Legados — carrega uma mini-pauta MININED (.xlsx,
uma turma+disciplina+ano letivo por ficheiro) e regista os alunos, a
matrícula e as notas do trimestre em curso, reaproveitando por inteiro
o motor de avaliação já existente (TipoAvaliacaoConfig/Avaliacao/
NotaAvaliacao — ver cruds/diario.py).

Fluxo em dois passos, sem tabela de rascunho (não existe esse padrão
em nenhum outro sítio do código — ver matricula-wizard/CRM): o preview
só faz parsing e devolve JSON, nada é gravado na BD a não ser o
próprio ficheiro no storage; o Angular guarda o resultado (editável)
até o Gestor confirmar, e só aí tudo é criado — ver
pre_visualizar_mini_pauta / confirmar_importacao_mini_pauta.
"""
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO

from fastapi import HTTPException
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.limites_plano import garantir_vaga_para_alunos
from app.database.models_academico import Curso, Disciplina, GradeCurricular, SerieAno, Turma
from app.database.models_diario import Avaliacao, PeriodoAvaliacao, TipoAvaliacaoConfig
from app.database.models_importacao import LoteImportacao, LoteImportacaoAluno
from app.database.models_matricula import Matricula
from app.database.models_pessoas import Aluno, AlunoDocumento, AlunoResponsavel
from app.schemas.academico import CursoCreate, DisciplinaCreate, SerieAnoCreate, TurmaCreate
from app.schemas.configuracoes import TipoAvaliacaoCreate
from app.schemas.diario import AvaliacaoCreate, NotaAvaliacaoAluno, NotaAvaliacaoLoteCreate, PeriodoAvaliacaoCreate
from app.schemas.importacao import (
    AlunoDetectado, EntidadeRefOuNova, DesfazerImportacaoResposta, ImportacaoMiniPautaConfirmar,
    ImportacaoMiniPautaResposta, MetadadosDetectados, NotaTrimestreDetectada, PreviewMiniPautaResposta,
    ResumoImportacao, ResumoPreview, TrimestreDetectado
)
from app.cruds import academico as academico_crud
from app.cruds import configuracoes as configuracoes_crud
from app.cruds import diario as diario_crud

_TIPOS_FICHEIRO_ACEITES = {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
_TAMANHO_MAXIMO_MINI_PAUTA = 5 * 1024 * 1024  # 5 MB

# Estrutura fixa do modelo MININED (confirmada em dois ficheiros reais
# — ver plano da funcionalidade): linha 12 = metadados, 13 = bandas de
# trimestre, 14 = cabeçalhos de coluna, 15+ = alunos.
_LINHA_METADADOS = 12
_LINHA_BANDAS = 13
_LINHA_CABECALHOS = 14
_LINHA_PRIMEIRO_ALUNO = 15

_DATA_NASCIMENTO_SENTINELA = date(1900, 1, 1)

_RE_PESO = re.compile(r"([0-9]*\.?[0-9]+)\s*\*\s*([A-Z]+)\d+")
_RE_SUM_MEDIA = re.compile(r"SUM\(\s*([A-Z]+)\d+\s*\+\s*([A-Z]+)\d+\s*\)\s*/\s*([0-9]+)")


# ==========================================
# PARSER (puro — sem acesso à BD)
# ==========================================
def _ler_decimal(valor) -> Decimal | None:
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


def _ler_linha_metadados(ws) -> dict[str, str]:
    """Linha 12: células fundidas no formato "LABEL:   valor" — só a
    célula âncora de cada bloco fundido tem valor, as outras vêm None."""
    valores: dict[str, str] = {}
    for col in range(1, ws.max_column + 1):
        bruto = ws.cell(_LINHA_METADADOS, col).value
        if bruto is None:
            continue
        texto = str(bruto).strip()
        if ":" not in texto:
            continue
        chave, _, valor = texto.partition(":")
        valores[chave.strip().upper()] = valor.strip()
    return valores


def _detectar_bandas_trimestre(ws) -> list[tuple[str, int]]:
    """[(nome_banda, coluna_inicio)] — só as bandas da linha 13 que
    contêm "TRIMESTRE" (ignora "CLASSIFICAÇÃO GERAL", fora de âmbito)."""
    bandas = []
    for col in range(1, ws.max_column + 1):
        bruto = ws.cell(_LINHA_BANDAS, col).value
        if bruto is None:
            continue
        texto = str(bruto).strip()
        if "TRIMESTRE" in texto.upper():
            bandas.append((texto, col))
    return bandas


def _detectar_colunas_banda(ws, col_inicio: int, col_fim: int) -> dict[str, int]:
    colunas: dict[str, int] = {}
    for col in range(col_inicio, col_fim + 1):
        bruto = ws.cell(_LINHA_CABECALHOS, col).value
        if bruto is None:
            continue
        nome = str(bruto).strip().upper()
        if nome in ("MACT", "PT", "MT"):
            colunas[nome] = col
    return colunas


def _extrair_pesos_formula(formula: str | None, coluna_mact: str, coluna_pt: str) -> tuple[Decimal, Decimal, bool]:
    """Lê a fórmula da coluna MT (nunca o valor calculado) e tenta
    reconhecer um dos dois padrões vistos nos ficheiros reais:
    ponderado (ex.: 0.4*G+0.6*H) ou média simples (SUM(x+y)/2). Sem
    reconhecer nenhum, cai em 50/50 e assinala
    peso_detectado_automaticamente=False para o Gestor rever no preview."""
    if not formula:
        return Decimal("50"), Decimal("50"), False
    formula_upper = formula.upper()

    pesos = _RE_PESO.findall(formula_upper)
    if len(pesos) == 2:
        mapa = {coluna: Decimal(peso) * 100 for peso, coluna in pesos}
        if coluna_mact in mapa and coluna_pt in mapa:
            return mapa[coluna_mact], mapa[coluna_pt], True

    soma = _RE_SUM_MEDIA.search(formula_upper)
    if soma:
        col_a, col_b, divisor = soma.groups()
        if {col_a, col_b} == {coluna_mact, coluna_pt} and divisor == "2":
            return Decimal("50"), Decimal("50"), True

    return Decimal("50"), Decimal("50"), False


def _parsear_mini_pauta(conteudo: bytes) -> dict:
    try:
        wb = load_workbook(BytesIO(conteudo), data_only=False)
    except Exception:
        raise HTTPException(status_code=400, detail="Não foi possível ler o ficheiro — confirme que é um .xlsx válido.")
    ws = wb.active

    bandas = _detectar_bandas_trimestre(ws)
    if not bandas:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível identificar as colunas MACT/PT/MT — este ficheiro não segue o modelo de mini-pauta esperado."
        )

    ancoras_linha13 = sorted(
        col for col in range(1, ws.max_column + 1) if ws.cell(_LINHA_BANDAS, col).value is not None
    )

    trimestres = []
    for nome_banda, col_inicio in bandas:
        proximas = [c for c in ancoras_linha13 if c > col_inicio]
        col_fim = (min(proximas) - 1) if proximas else ws.max_column

        colunas = _detectar_colunas_banda(ws, col_inicio, col_fim)
        if "MACT" not in colunas or "PT" not in colunas:
            raise HTTPException(
                status_code=400,
                detail=f'Não foi possível identificar as colunas MACT/PT em "{nome_banda}" — confirme que o ficheiro segue o modelo de mini-pauta.'
            )

        formula_mt = None
        if "MT" in colunas:
            for r in range(_LINHA_PRIMEIRO_ALUNO, min(_LINHA_PRIMEIRO_ALUNO + 10, ws.max_row + 1)):
                bruto = ws.cell(r, colunas["MT"]).value
                if bruto is not None:
                    formula_mt = str(bruto)
                    break

        col_letra_mact = get_column_letter(colunas["MACT"])
        col_letra_pt = get_column_letter(colunas["PT"])
        peso_mact, peso_pt, detectado = _extrair_pesos_formula(formula_mt, col_letra_mact, col_letra_pt)

        trimestres.append({
            "nome": nome_banda,
            "colunas": colunas,
            "formula_mt_original": formula_mt,
            "peso_mact": peso_mact,
            "peso_pt": peso_pt,
            "peso_detectado_automaticamente": detectado,
            "tem_dados": False,  # atualizado abaixo, ao percorrer os alunos
        })

    colunas_conhecidas = max(
        (col for col in range(1, ws.max_column + 1) if ws.cell(_LINHA_CABECALHOS, col).value is not None),
        default=0,
    )

    alunos = []
    r = _LINHA_PRIMEIRO_ALUNO
    while r <= ws.max_row:
        numero_raw = ws.cell(r, 1).value
        try:
            numero_pauta = int(numero_raw) if numero_raw is not None else None
        except (TypeError, ValueError):
            numero_pauta = None
        if numero_pauta is None:
            # Fim da lista de alunos (ex.: linha "ASSINATURA DO PROFESSOR").
            break

        nome_raw = ws.cell(r, 2).value
        nome_completo = str(nome_raw).strip() if nome_raw else ""
        if not nome_completo:
            r += 1
            continue

        anomalias: list[str] = []
        notas: dict[str, dict[str, Decimal | None]] = {}
        for trimestre in trimestres:
            colunas = trimestre["colunas"]
            mact = _ler_decimal(ws.cell(r, colunas["MACT"]).value)
            pt = _ler_decimal(ws.cell(r, colunas["PT"]).value)
            if mact is None and pt is None:
                anomalias.append(f'MACT e PT em branco em "{trimestre["nome"]}" — nenhuma nota será lançada para este trimestre.')
            else:
                trimestre["tem_dados"] = True
            notas[trimestre["nome"]] = {"mact": mact, "pt": pt}

        for col in range(colunas_conhecidas + 1, ws.max_column + 1):
            if ws.cell(r, col).value is not None:
                anomalias.append(f"Valor não identificado na coluna {get_column_letter(col)} desta linha (fora da tabela) — ignorado.")

        alunos.append({
            "linha_excel": r,
            "numero_pauta": numero_pauta,
            "nome_completo": nome_completo,
            "notas": notas,
            "anomalias": anomalias,
        })
        r += 1

    if not alunos:
        raise HTTPException(status_code=400, detail="Não foi encontrado nenhum aluno neste ficheiro — confirme que segue o modelo de mini-pauta.")

    metadados_raw = _ler_linha_metadados(ws)
    ano_letivo_raw = metadados_raw.get("ANO LECTIVO") or metadados_raw.get("ANO LETIVO")
    ano_letivo = None
    if ano_letivo_raw:
        encontrado = re.search(r"(\d{4})", ano_letivo_raw)
        if encontrado:
            ano_letivo = int(encontrado.group(1))

    metadados = {
        "disciplina_nome": metadados_raw.get("DISCIPLINA"),
        "sala": metadados_raw.get("SALA"),
        "turma_nome_codigo": metadados_raw.get("TURMA"),
        "turno": metadados_raw.get("TURNO"),
        "ano_letivo_raw": ano_letivo_raw,
        "ano_letivo": ano_letivo,
    }

    return {"metadados": metadados, "trimestres": trimestres, "alunos": alunos}


# ==========================================
# PRÉ-VISUALIZAÇÃO
# ==========================================
async def pre_visualizar_mini_pauta(
    db: AsyncSession, tenant_id, nome_ficheiro: str, content_type: str, conteudo: bytes
) -> PreviewMiniPautaResposta:
    if content_type not in _TIPOS_FICHEIRO_ACEITES:
        raise HTTPException(status_code=400, detail=f"Formato não aceite ({content_type}). Envie um ficheiro .xlsx.")
    if len(conteudo) > _TAMANHO_MAXIMO_MINI_PAUTA:
        raise HTTPException(status_code=400, detail="O ficheiro não pode passar de 5 MB.")

    dados = _parsear_mini_pauta(conteudo)

    nomes_alunos = [a["nome_completo"] for a in dados["alunos"]]
    existentes: dict[str, uuid.UUID] = {}
    if nomes_alunos:
        resultado = await db.execute(
            select(Aluno.id, Aluno.nome_completo).where(Aluno.tenant_id == tenant_id, Aluno.nome_completo.in_(nomes_alunos))
        )
        for aluno_id, nome in resultado.all():
            existentes[nome] = aluno_id

    total_com_anomalias = 0
    total_correspondencias = 0
    alunos_resposta = []
    for aluno in dados["alunos"]:
        aluno_existente_id = existentes.get(aluno["nome_completo"])
        anomalias = list(aluno["anomalias"])
        if aluno_existente_id:
            anomalias.insert(0, "Já existe um aluno com este nome nesta escola — confirme se é a mesma pessoa.")
            total_correspondencias += 1
        if anomalias:
            total_com_anomalias += 1
        alunos_resposta.append(AlunoDetectado(
            linha_excel=aluno["linha_excel"],
            numero_pauta=aluno["numero_pauta"],
            nome_completo=aluno["nome_completo"],
            aluno_existente_id=aluno_existente_id,
            notas={nome: NotaTrimestreDetectada(**valores) for nome, valores in aluno["notas"].items()},
            anomalias=anomalias,
        ))

    # Só o ficheiro em si — nenhuma linha na BD ainda (ver docstring do módulo).
    chave = storage.gerar_chave(tenant_id, "importacao", nome_ficheiro)
    await storage.guardar_ficheiro(chave, conteudo, content_type)

    trimestres_resposta = [
        TrimestreDetectado(
            nome=t["nome"], tem_dados=t["tem_dados"], formula_mt_original=t["formula_mt_original"],
            peso_mact=t["peso_mact"], peso_pt=t["peso_pt"], peso_detectado_automaticamente=t["peso_detectado_automaticamente"],
        )
        for t in dados["trimestres"]
    ]

    return PreviewMiniPautaResposta(
        metadados=MetadadosDetectados(**dados["metadados"], chave_storage_ficheiro=chave),
        trimestres=trimestres_resposta,
        alunos=alunos_resposta,
        resumo=ResumoPreview(
            total_linhas=len(alunos_resposta),
            total_com_anomalias=total_com_anomalias,
            total_correspondencias_nome_existente=total_correspondencias,
        ),
    )


# ==========================================
# CONFIRMAÇÃO — find-or-create nas entidades partilhadas + criação do plantel
# ==========================================
def _gerar_matricula_interna_import() -> str:
    return f"IMP-{uuid.uuid4().hex[:8].upper()}"


async def _gerar_matricula_interna_unica(db: AsyncSession, tenant_id) -> str:
    for _ in range(20):
        candidato = _gerar_matricula_interna_import()
        existe = (await db.execute(
            select(Aluno.id).where(Aluno.tenant_id == tenant_id, Aluno.matricula_interna == candidato)
        )).scalars().first()
        if not existe:
            return candidato
    raise HTTPException(status_code=500, detail="Não foi possível gerar um número de matrícula interna único — tente novamente.")


async def _obter_ou_criar_curso(db: AsyncSession, tenant_id, ref: EntidadeRefOuNova) -> Curso:
    if ref.id:
        curso = (await db.execute(select(Curso).where(Curso.id == ref.id, Curso.tenant_id == tenant_id))).scalars().first()
        if not curso:
            raise HTTPException(status_code=404, detail="Curso não encontrado na sua instituição.")
        return curso
    nome = ref.nome_novo.strip()
    existente = (await db.execute(select(Curso).where(Curso.tenant_id == tenant_id, Curso.nome == nome))).scalars().first()
    if existente:
        return existente
    return await academico_crud.criar_curso(db, tenant_id, CursoCreate(nome=nome))


async def _obter_ou_criar_serie_ano(db: AsyncSession, tenant_id, ref: EntidadeRefOuNova, curso_id) -> SerieAno:
    if ref.id:
        serie = (await db.execute(select(SerieAno).where(SerieAno.id == ref.id, SerieAno.tenant_id == tenant_id))).scalars().first()
        if not serie:
            raise HTTPException(status_code=404, detail="Série/Ano não encontrada na sua instituição.")
        return serie
    nome = ref.nome_novo.strip()
    existente = (await db.execute(
        select(SerieAno).where(SerieAno.tenant_id == tenant_id, SerieAno.curso_id == curso_id, SerieAno.nome == nome)
    )).scalars().first()
    if existente:
        return existente
    return await academico_crud.criar_serie_ano(db, tenant_id, SerieAnoCreate(curso_id=curso_id, nome=nome))


async def _obter_ou_criar_turma(db: AsyncSession, tenant_id, ref: EntidadeRefOuNova, serie_ano_id, ano_letivo: int) -> Turma:
    if ref.id:
        turma = (await db.execute(select(Turma).where(Turma.id == ref.id, Turma.tenant_id == tenant_id))).scalars().first()
        if not turma:
            raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")
        return turma
    nome = ref.nome_novo.strip()
    existente = (await db.execute(
        select(Turma).where(
            Turma.tenant_id == tenant_id, Turma.serie_ano_id == serie_ano_id,
            Turma.nome_codigo == nome, Turma.ano_letivo == ano_letivo,
        )
    )).scalars().first()
    if existente:
        return existente
    return await academico_crud.criar_turma(db, tenant_id, TurmaCreate(serie_ano_id=serie_ano_id, nome_codigo=nome, ano_letivo=ano_letivo))


async def _obter_ou_criar_disciplina(db: AsyncSession, tenant_id, ref: EntidadeRefOuNova) -> Disciplina:
    if ref.id:
        disciplina = (await db.execute(select(Disciplina).where(Disciplina.id == ref.id, Disciplina.tenant_id == tenant_id))).scalars().first()
        if not disciplina:
            raise HTTPException(status_code=404, detail="Disciplina não encontrada na sua instituição.")
        return disciplina
    nome = ref.nome_novo.strip()
    existente = (await db.execute(select(Disciplina).where(Disciplina.tenant_id == tenant_id, Disciplina.nome == nome))).scalars().first()
    if existente:
        return existente
    return await academico_crud.criar_disciplina(db, tenant_id, DisciplinaCreate(nome=nome))


async def _obter_ou_criar_periodo_avaliacao(db: AsyncSession, tenant_id, nome: str) -> PeriodoAvaliacao:
    existente = (await db.execute(
        select(PeriodoAvaliacao).where(PeriodoAvaliacao.tenant_id == tenant_id, PeriodoAvaliacao.nome == nome)
    )).scalars().first()
    if existente:
        return existente
    return await diario_crud.criar_periodo_avaliacao(db, tenant_id, PeriodoAvaliacaoCreate(nome=nome))


async def _obter_ou_criar_tipo_avaliacao(db: AsyncSession, tenant_id, nome: str) -> TipoAvaliacaoConfig:
    existente = (await db.execute(
        select(TipoAvaliacaoConfig).where(TipoAvaliacaoConfig.tenant_id == tenant_id, TipoAvaliacaoConfig.nome == nome)
    )).scalars().first()
    if existente:
        return existente
    return await configuracoes_crud.criar_tipo_avaliacao(db, tenant_id, TipoAvaliacaoCreate(nome=nome, requer_agendamento=False))


async def _obter_ou_criar_avaliacao(
    db: AsyncSession, utilizador: dict, turma_id, disciplina_id, periodo_nome: str, tipo: str, peso: Decimal
) -> Avaliacao:
    tenant_id = utilizador["tenant_id"]
    existente = (await db.execute(
        select(Avaliacao).where(
            Avaliacao.tenant_id == tenant_id, Avaliacao.turma_id == turma_id, Avaliacao.disciplina_id == disciplina_id,
            Avaliacao.periodo_avaliacao == periodo_nome, Avaliacao.tipo_avaliacao == tipo,
        )
    )).scalars().first()
    if existente:
        return existente
    return await diario_crud.criar_avaliacao(
        db, utilizador, turma_id, disciplina_id,
        AvaliacaoCreate(periodo_avaliacao=periodo_nome, titulo=f"{tipo} – {periodo_nome}", tipo_avaliacao=tipo, peso=peso),
    )


async def confirmar_importacao_mini_pauta(db: AsyncSession, utilizador: dict, dados: ImportacaoMiniPautaConfirmar) -> ImportacaoMiniPautaResposta:
    tenant_id = utilizador["tenant_id"]

    curso = await _obter_ou_criar_curso(db, tenant_id, dados.curso)
    serie_ano = await _obter_ou_criar_serie_ano(db, tenant_id, dados.serie_ano, curso.id)
    turma = await _obter_ou_criar_turma(db, tenant_id, dados.turma, serie_ano.id, dados.ano_letivo)
    disciplina = await _obter_ou_criar_disciplina(db, tenant_id, dados.disciplina)

    ja_na_grade = (await db.execute(
        select(GradeCurricular.id).where(GradeCurricular.serie_ano_id == serie_ano.id, GradeCurricular.disciplina_id == disciplina.id)
    )).scalars().first()
    if not ja_na_grade:
        db.add(GradeCurricular(tenant_id=tenant_id, serie_ano_id=serie_ano.id, disciplina_id=disciplina.id))
        await db.flush()

    avaliacoes_por_trimestre: dict[str, dict[str, uuid.UUID]] = {}
    for trimestre in dados.trimestres:
        if not trimestre.tem_dados:
            continue
        await _obter_ou_criar_periodo_avaliacao(db, tenant_id, trimestre.nome)
        for tipo, peso in (("MACT", trimestre.peso_mact), ("PT", trimestre.peso_pt)):
            await _obter_ou_criar_tipo_avaliacao(db, tenant_id, tipo)
            avaliacao = await _obter_ou_criar_avaliacao(db, utilizador, turma.id, disciplina.id, trimestre.nome, tipo, peso)
            avaliacoes_por_trimestre.setdefault(trimestre.nome, {})[tipo] = avaliacao.id

    lote = LoteImportacao(
        tenant_id=tenant_id,
        criado_por_usuario_id=utilizador["usuario_id"],
        nome_ficheiro_original=dados.nome_ficheiro_original,
        chave_storage_ficheiro=dados.chave_storage_ficheiro,
        turma_id=turma.id,
        disciplina_id=disciplina.id,
        ano_letivo=dados.ano_letivo,
    )
    db.add(lote)
    await db.flush()

    await garantir_vaga_para_alunos(
        db, tenant_id, sum(1 for a in dados.alunos if a.acao == "CRIAR_NOVO_ALUNO")
    )

    total_criados = 0
    total_reaproveitados = 0
    alunos_pendentes_nascimento: list[str] = []
    matricula_id_por_nome: dict[str, uuid.UUID] = {}

    for aluno_confirmado in dados.alunos:
        if aluno_confirmado.acao == "REUTILIZAR_ALUNO_EXISTENTE":
            if not aluno_confirmado.aluno_existente_id:
                raise HTTPException(status_code=400, detail=f'Aluno "{aluno_confirmado.nome_completo}": indique aluno_existente_id para reutilizar.')
            aluno = (await db.execute(
                select(Aluno).where(Aluno.id == aluno_confirmado.aluno_existente_id, Aluno.tenant_id == tenant_id)
            )).scalars().first()
            if not aluno:
                raise HTTPException(status_code=404, detail=f'Aluno existente não encontrado para "{aluno_confirmado.nome_completo}".')
            aluno_pre_existente = True
            nascimento_estimada = False
            total_reaproveitados += 1
        elif aluno_confirmado.acao == "CRIAR_NOVO_ALUNO":
            matricula_interna = await _gerar_matricula_interna_unica(db, tenant_id)
            aluno = Aluno(
                tenant_id=tenant_id,
                matricula_interna=matricula_interna,
                nome_completo=aluno_confirmado.nome_completo.strip(),
                data_nascimento=_DATA_NASCIMENTO_SENTINELA,
            )
            db.add(aluno)
            await db.flush()
            aluno_pre_existente = False
            nascimento_estimada = True
            alunos_pendentes_nascimento.append(aluno_confirmado.nome_completo)
            total_criados += 1
        else:
            raise HTTPException(status_code=400, detail=f'Ação inválida "{aluno_confirmado.acao}" para "{aluno_confirmado.nome_completo}".')

        matricula = (await db.execute(
            select(Matricula).where(Matricula.aluno_id == aluno.id, Matricula.turma_id == turma.id, Matricula.ano_letivo == dados.ano_letivo)
        )).scalars().first()
        if not matricula:
            matricula = Matricula(tenant_id=tenant_id, aluno_id=aluno.id, turma_id=turma.id, ano_letivo=dados.ano_letivo)
            db.add(matricula)
            await db.flush()

        db.add(LoteImportacaoAluno(
            tenant_id=tenant_id, lote_importacao_id=lote.id, aluno_id=aluno.id, matricula_id=matricula.id,
            aluno_pre_existente=aluno_pre_existente, data_nascimento_estimada=nascimento_estimada,
        ))
        matricula_id_por_nome[aluno_confirmado.nome_completo] = matricula.id

    await db.flush()

    total_notas = 0
    for trimestre in dados.trimestres:
        avaliacoes_tipo = avaliacoes_por_trimestre.get(trimestre.nome)
        if not avaliacoes_tipo:
            continue
        for tipo, avaliacao_id in avaliacoes_tipo.items():
            notas_lote = []
            for aluno_confirmado in dados.alunos:
                nota_trimestre = aluno_confirmado.notas.get(trimestre.nome)
                if not nota_trimestre:
                    continue
                valor = nota_trimestre.mact if tipo == "MACT" else nota_trimestre.pt
                if valor is None:
                    continue
                matricula_id = matricula_id_por_nome.get(aluno_confirmado.nome_completo)
                if matricula_id is None:
                    continue
                notas_lote.append(NotaAvaliacaoAluno(matricula_id=matricula_id, valor_nota=valor))
            if notas_lote:
                total_notas += await diario_crud.lancar_notas_avaliacao_lote(
                    db, utilizador, avaliacao_id, NotaAvaliacaoLoteCreate(notas=notas_lote)
                )

    lote.total_alunos_criados = total_criados
    lote.total_alunos_reaproveitados = total_reaproveitados
    lote.total_notas_lancadas = total_notas
    await db.commit()
    await db.refresh(lote)

    return ImportacaoMiniPautaResposta(
        lote_importacao_id=lote.id,
        estado=lote.estado,
        resumo=ResumoImportacao(
            total_alunos_criados=total_criados, total_alunos_reaproveitados=total_reaproveitados, total_notas_lancadas=total_notas,
        ),
        alunos_com_data_nascimento_pendente=alunos_pendentes_nascimento,
    )


# ==========================================
# HISTÓRICO / DESFAZER
# ==========================================
async def listar_lotes(db: AsyncSession, tenant_id) -> list[LoteImportacao]:
    return (await db.execute(
        select(LoteImportacao).where(LoteImportacao.tenant_id == tenant_id).order_by(LoteImportacao.data_criacao.desc())
    )).scalars().all()


async def desfazer_importacao(db: AsyncSession, utilizador: dict, lote_id: uuid.UUID) -> DesfazerImportacaoResposta:
    """
    Desfaz só a parte de maior risco de um lote — o plantel e as notas
    que ele criou (Matricula, cascata para NotaAvaliacao/RegistroNota/
    RegistroFrequencia, e o próprio Aluno quando foi criado por este
    lote e continua sem mais nada ligado). Entidades partilhadas
    (Turma/Disciplina/PeriodoAvaliacao/TipoAvaliacaoConfig/Avaliacao)
    nunca são tocadas aqui — podem já estar em uso por lançamentos
    manuais feitos logo a seguir; a limpeza dessas, se necessária, é
    pelos ecrãs normais (Académico/Configurações/Diário).
    """
    tenant_id = utilizador["tenant_id"]
    lote = (await db.execute(
        select(LoteImportacao).where(LoteImportacao.id == lote_id, LoteImportacao.tenant_id == tenant_id)
    )).scalars().first()
    if not lote:
        raise HTTPException(status_code=404, detail="Importação não encontrada na sua instituição.")
    if lote.estado != "CONCLUIDO":
        raise HTTPException(status_code=400, detail="Esta importação já foi desfeita anteriormente.")

    itens = (await db.execute(
        select(LoteImportacaoAluno).where(LoteImportacaoAluno.lote_importacao_id == lote.id)
    )).scalars().all()

    removidos = 0
    mantidos = 0
    for item in itens:
        matricula = (await db.execute(select(Matricula).where(Matricula.id == item.matricula_id))).scalars().first()
        if matricula:
            await db.delete(matricula)  # cascade apaga NotaAvaliacao/RegistroNota/RegistroFrequencia ligados

        if item.aluno_pre_existente:
            mantidos += 1
            continue

        outra_matricula = (await db.execute(
            select(Matricula.id).where(Matricula.aluno_id == item.aluno_id, Matricula.id != item.matricula_id)
        )).scalars().first()
        outro_documento = (await db.execute(
            select(AlunoDocumento.id).where(AlunoDocumento.aluno_id == item.aluno_id)
        )).scalars().first()
        outro_responsavel = (await db.execute(
            select(AlunoResponsavel.id).where(AlunoResponsavel.aluno_id == item.aluno_id)
        )).scalars().first()
        if outra_matricula or outro_documento or outro_responsavel:
            mantidos += 1
            continue

        aluno = (await db.execute(select(Aluno).where(Aluno.id == item.aluno_id))).scalars().first()
        if aluno:
            await db.delete(aluno)
        removidos += 1

    lote.estado = "DESFEITO"
    lote.data_desfeito = datetime.now(timezone.utc)
    lote.desfeito_por_usuario_id = utilizador["usuario_id"]
    await db.commit()

    return DesfazerImportacaoResposta(
        estado=lote.estado, alunos_removidos=removidos, alunos_mantidos=mantidos,
        mensagem=f"Importação desfeita — {removidos} aluno(s) removido(s), {mantidos} mantido(s) (matrícula/dados adicionais preservados)."
    )
