"""
Acesso a dados do Portal do Aluno/Responsável — vista de leitura,
agregando dados já produzidos por outros módulos (Diário, Horários,
Financeiro) para os logins ALUNO/RESPONSAVEL, sempre restrita aos
seus próprios educandos.

Este módulo não duplica regras de negócio: só resolve "que aluno_id(s)
este login pode ver" e delega a leitura em si aos cruds já existentes
(cruds/horarios.py, cruds/financeiro.py), que continuam a ser os
únicos donos das suas tabelas.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models_academico import Disciplina, ObjetivoAprendizagem, Turma
from app.database.models_diario import RegistroFrequencia, RegistroNota
from app.database.models_financeiro import ContratoFinanceiro, FaturaMensalidade
from app.database.models_lms import MaterialAula
from app.database.models_matricula import Matricula, PedidoRematricula
from app.database.models_pessoas import Aluno
from app.database.models import Usuario
from app.cruds import alunos as crud_alunos
from app.cruds import financeiro as crud_financeiro
from app.cruds import horarios as crud_horarios
from app.cruds import matriculas as crud_matriculas
from app.cruds import notificacoes as crud_notificacoes
from app.cruds import tarefas as crud_tarefas
from app.cruds import lms as crud_lms
from app.core.prof_virtual import perguntar_prof_virtual
from app.schemas.lms import LMSSubmeterTentativa, ProfVirtualPerguntaCreate

# Resolução de acesso ("que aluno_id este login pode ver") vive em
# cruds/alunos.py — também é precisa em Documentos (pedidos do
# aluno/responsável), por isso deixou de estar duplicada aqui.
_resolver_meus_alunos = crud_alunos.resolver_meus_alunos
_garantir_aluno_permitido = crud_alunos.garantir_aluno_permitido


async def _obter_matricula_atual(db: AsyncSession, tenant_id, aluno_id: uuid.UUID) -> Matricula | None:
    """
    A matrícula "atual" do aluno para efeitos do Portal: prioriza uma
    matrícula ATIVO (a mais recente, se houver mais que uma) e só cai
    para a mais recente de qualquer status se não houver nenhuma ativa
    — a data de criação sozinha não é fiável aqui (uma matrícula
    ATIVO mais antiga continua a ser "a atual" mesmo que exista um
    registo TRANCADO/TRANSFERIDO mais recente).
    """
    ordem = (Matricula.ano_letivo.desc(), Matricula.data_matricula.desc())
    ativa = (await db.execute(
        select(Matricula)
        .where(Matricula.aluno_id == aluno_id, Matricula.tenant_id == tenant_id, Matricula.status_matricula == "ATIVO")
        .order_by(*ordem)
    )).scalars().first()
    if ativa:
        return ativa
    return (await db.execute(
        select(Matricula)
        .where(Matricula.aluno_id == aluno_id, Matricula.tenant_id == tenant_id)
        .order_by(*ordem)
    )).scalars().first()


async def _tem_propina_em_atraso(db: AsyncSession, tenant_id, matricula_id: uuid.UUID) -> bool:
    """Para o resumo em /portal/meus-educandos — um responsável pode
    ter vários educandos, cada um com o seu próprio contrato/faturas;
    isto deixa o Portal assinalar quem precisa de atenção sem o
    responsável ter de abrir o financeiro de cada um. Reaproveita
    calcular_situacao_fatura (a mesma conta usada em Financeiro e nos
    Indicadores) — "ATRASADO" nunca fica gravado, é sempre calculado."""
    faturas_pendentes = (await db.execute(
        select(FaturaMensalidade)
        .join(ContratoFinanceiro, ContratoFinanceiro.id == FaturaMensalidade.contrato_id)
        .where(
            ContratoFinanceiro.matricula_id == matricula_id, FaturaMensalidade.tenant_id == tenant_id,
            FaturaMensalidade.status_pagamento == "PENDENTE",
        )
    )).scalars().all()
    return any(crud_financeiro.calcular_situacao_fatura(f)["status_efetivo"] == "ATRASADO" for f in faturas_pendentes)


async def _situacao_rematricula(db: AsyncSession, tenant_id, matricula: Matricula | None) -> dict:
    """Rematrícula self-service (ver pedir_rematricula, abaixo): só faz
    sentido oferecer quando a matrícula atual está ATIVO e ainda não
    existe nenhuma matrícula para o ano seguinte — reaproveita a MESMA
    verificação de RN05 que criar_matricula aplica de facto, para o
    Portal nunca prometer algo que a Secretaria depois recusa."""
    nao_disponivel = {"elegivel_rematricula": False, "bloqueado_rematricula_por_atraso": False, "pedido_rematricula_confirmado": False, "ano_letivo_destino_rematricula": None}
    if not matricula or matricula.status_matricula != "ATIVO":
        return nao_disponivel

    ano_destino = matricula.ano_letivo + 1
    ja_renovado = (await db.execute(
        select(Matricula.id).where(
            Matricula.tenant_id == tenant_id, Matricula.aluno_id == matricula.aluno_id, Matricula.ano_letivo == ano_destino
        )
    )).scalars().first()
    if ja_renovado:
        return nao_disponivel

    bloqueado = await crud_matriculas.tem_mensalidade_em_atraso_de_ano_anterior(db, tenant_id, matricula.aluno_id, ano_destino)
    pedido = (await db.execute(
        select(PedidoRematricula.id).where(
            PedidoRematricula.tenant_id == tenant_id, PedidoRematricula.aluno_id == matricula.aluno_id,
            PedidoRematricula.ano_letivo_destino == ano_destino,
        )
    )).scalars().first()

    return {
        "elegivel_rematricula": True,
        "bloqueado_rematricula_por_atraso": bloqueado,
        "pedido_rematricula_confirmado": pedido is not None,
        "ano_letivo_destino_rematricula": ano_destino,
    }


# ==========================================
# A. MEUS EDUCANDOS
# ==========================================
async def listar_meus_educandos(db: AsyncSession, tenant_id, utilizador: dict) -> list[dict]:
    aluno_ids = await _resolver_meus_alunos(db, tenant_id, utilizador)
    if not aluno_ids:
        return []

    alunos = (await db.execute(
        select(Aluno).where(Aluno.id.in_(aluno_ids), Aluno.tenant_id == tenant_id)
    )).scalars().all()

    resultado = []
    for aluno in alunos:
        matricula = await _obter_matricula_atual(db, tenant_id, aluno.id)
        nome_turma = None
        tem_propina_em_atraso = False
        if matricula:
            nome_turma = (await db.execute(
                select(Turma.nome_codigo).where(Turma.id == matricula.turma_id)
            )).scalar_one_or_none()
            tem_propina_em_atraso = await _tem_propina_em_atraso(db, tenant_id, matricula.id)
        resultado.append({
            "aluno_id": aluno.id,
            "nome_completo": aluno.nome_completo,
            "matricula_interna": aluno.matricula_interna,
            "matricula_id": matricula.id if matricula else None,
            "status_matricula": matricula.status_matricula if matricula else None,
            "ano_letivo": matricula.ano_letivo if matricula else None,
            "nome_turma": nome_turma,
            "tem_propina_em_atraso": tem_propina_em_atraso,
            **(await _situacao_rematricula(db, tenant_id, matricula)),
        })
    return resultado


# ==========================================
# A2. REMATRÍCULA SELF-SERVICE
# ==========================================
async def pedir_rematricula(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> dict:
    """O encarregado (ou o próprio aluno) confirma interesse em renovar
    a matrícula para o ano letivo seguinte. Não cria a Matrícula em si
    — só sinaliza a Secretaria/Gestor (que continuam a escolher a
    turma de destino no ecrã de Rematrícula) e fica visível lá como
    "família já confirmou interesse"."""
    aluno = await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        raise HTTPException(status_code=400, detail="Este educando não tem uma matrícula ativa para renovar.")

    ano_destino = matricula.ano_letivo + 1
    ja_renovado = (await db.execute(
        select(Matricula.id).where(
            Matricula.tenant_id == tenant_id, Matricula.aluno_id == aluno_id, Matricula.ano_letivo == ano_destino
        )
    )).scalars().first()
    if ja_renovado:
        raise HTTPException(status_code=400, detail="Este educando já tem matrícula para o próximo ano letivo.")

    if await crud_matriculas.tem_mensalidade_em_atraso_de_ano_anterior(db, tenant_id, aluno_id, ano_destino):
        raise HTTPException(
            status_code=403,
            detail="Existem mensalidades em atraso que bloqueiam a renovação — regularize a situação em Financeiro antes de pedir a rematrícula."
        )

    existente = (await db.execute(
        select(PedidoRematricula).where(
            PedidoRematricula.tenant_id == tenant_id, PedidoRematricula.aluno_id == aluno_id,
            PedidoRematricula.ano_letivo_destino == ano_destino,
        )
    )).scalars().first()
    if not existente:
        existente = PedidoRematricula(
            tenant_id=tenant_id, aluno_id=aluno_id, matricula_atual_id=matricula.id,
            ano_letivo_destino=ano_destino, solicitado_por_usuario_id=utilizador["usuario_id"],
        )
        db.add(existente)
        await db.commit()

        destinatarios = (await db.execute(
            select(Usuario.id).where(Usuario.tenant_id == tenant_id, Usuario.perfil_acesso.in_(["GESTOR", "SECRETARIA"]))
        )).scalars().all()
        if destinatarios:
            await crud_notificacoes.criar_notificacoes_em_lote(
                db, tenant_id, list(destinatarios), tipo="REMATRICULA",
                titulo="Pedido de rematrícula",
                mensagem=f"A família de {aluno.nome_completo} confirmou interesse em renovar a matrícula para {ano_destino}.",
                link="/rematricula"
            )

    return {"pedido_rematricula_confirmado": True, "ano_letivo_destino_rematricula": ano_destino}


# ==========================================
# B. HORÁRIO DO EDUCANDO
# ==========================================
async def obter_horario_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        return []
    return await crud_horarios.listar_grade_da_turma(db, tenant_id, matricula.turma_id)


# ==========================================
# C. BOLETIM (NOTAS + FREQUÊNCIA) DO EDUCANDO
# ==========================================
async def obter_boletim_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> dict:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        return {"disciplinas": []}

    notas = (await db.execute(
        select(RegistroNota, Disciplina.nome)
        .join(Disciplina, Disciplina.id == RegistroNota.disciplina_id)
        .where(RegistroNota.matricula_id == matricula.id, RegistroNota.tenant_id == tenant_id)
        .order_by(Disciplina.nome, RegistroNota.periodo_avaliacao)
    )).all()

    frequencias = (await db.execute(
        select(
            RegistroFrequencia.disciplina_id, Disciplina.nome,
            func.count(RegistroFrequencia.id), func.sum(RegistroFrequencia.faltas)
        )
        .join(Disciplina, Disciplina.id == RegistroFrequencia.disciplina_id)
        .where(RegistroFrequencia.matricula_id == matricula.id, RegistroFrequencia.tenant_id == tenant_id)
        .group_by(RegistroFrequencia.disciplina_id, Disciplina.nome)
    )).all()

    por_disciplina: dict[uuid.UUID, dict] = {}

    def _entrada(disciplina_id: uuid.UUID, nome_disciplina: str) -> dict:
        return por_disciplina.setdefault(disciplina_id, {
            "disciplina_id": disciplina_id,
            "nome_disciplina": nome_disciplina,
            "notas": [],
            "total_aulas": 0,
            "total_faltas": 0,
        })

    for nota, nome_disciplina in notas:
        entrada = _entrada(nota.disciplina_id, nome_disciplina)
        entrada["notas"].append({
            "periodo_avaliacao": nota.periodo_avaliacao,
            "tipo_avaliacao": nota.tipo_avaliacao,
            "data_avaliacao": nota.data_avaliacao,
            "valor_nota": nota.valor_nota,
        })

    for disciplina_id, nome_disciplina, total_aulas, total_faltas in frequencias:
        entrada = _entrada(disciplina_id, nome_disciplina)
        entrada["total_aulas"] = int(total_aulas or 0)
        entrada["total_faltas"] = int(total_faltas or 0)

    return {"disciplinas": sorted(por_disciplina.values(), key=lambda d: d["nome_disciplina"])}


# ==========================================
# D. FINANCEIRO (CONTRATO + FATURAS) DO EDUCANDO
# ==========================================
async def obter_financeiro_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> dict:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        return {"matricula_id": None, "contrato": None, "faturas": []}

    try:
        contrato = await crud_financeiro.obter_contrato_da_matricula(db, tenant_id, matricula.id, utilizador)
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"matricula_id": matricula.id, "contrato": None, "faturas": []}
        raise

    faturas = await crud_financeiro.listar_faturas_do_contrato(db, tenant_id, contrato.id, utilizador)
    return {
        "matricula_id": matricula.id,
        "contrato": {
            "id": contrato.id,
            "valor_total_anual": contrato.valor_total_anual,
            "quantidade_parcelas": contrato.quantidade_parcelas,
        },
        "faturas": faturas,
    }


# ==========================================
# E. TRABALHOS/TAREFAS DO EDUCANDO
# ==========================================
async def listar_tarefas_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        return []
    return await crud_tarefas.listar_tarefas_do_aluno(db, tenant_id, matricula.id)


# ==========================================
# F. MATERIAIS DE AULA (LMS mínimo) + PROF. VIRTUAL
# ==========================================
async def listar_materiais_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    """Materiais publicados para a turma atual do educando, agrupáveis por disciplina no front-end."""
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        return []

    linhas = (await db.execute(
        select(MaterialAula, Disciplina.nome)
        .join(Disciplina, Disciplina.id == MaterialAula.disciplina_id)
        .where(
            MaterialAula.turma_id == matricula.turma_id,
            MaterialAula.tenant_id == tenant_id,
            MaterialAula.publicado.is_(True)
        )
        .order_by(Disciplina.nome, MaterialAula.data_criacao.desc())
    )).all()

    return [
        {
            "id": material.id,
            "titulo": material.titulo,
            "disciplina_id": material.disciplina_id,
            "nome_disciplina": nome_disciplina,
            "data_criacao": material.data_criacao,
        }
        for material, nome_disciplina in linhas
    ]


async def _obter_material_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, material_id: uuid.UUID) -> MaterialAula:
    """Devolve o MaterialAula só se pertencer à turma atual do educando e estiver publicado — nunca deixa ver o de outra turma trocando o id no URL."""
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        raise HTTPException(status_code=404, detail="Material de aula não encontrado.")

    material = (await db.execute(
        select(MaterialAula).where(
            MaterialAula.id == material_id,
            MaterialAula.tenant_id == tenant_id,
            MaterialAula.turma_id == matricula.turma_id,
            MaterialAula.publicado.is_(True)
        )
    )).scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Material de aula não encontrado.")
    return material


async def obter_material_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, material_id: uuid.UUID) -> dict:
    material = await _obter_material_do_educando(db, tenant_id, utilizador, aluno_id, material_id)
    nome_objetivo = None
    if material.objetivo_aprendizagem_id:
        nome_objetivo = (await db.execute(
            select(ObjetivoAprendizagem.nome).where(ObjetivoAprendizagem.id == material.objetivo_aprendizagem_id)
        )).scalar_one_or_none()
    return {
        "id": material.id,
        "titulo": material.titulo,
        "corpo": material.corpo,
        "disciplina_id": material.disciplina_id,
        "nome_objetivo": nome_objetivo,
    }


async def perguntar_prof_virtual_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, dados: ProfVirtualPerguntaCreate) -> str:
    """Encaminha a pergunta do aluno ao Prof. Virtual, com o material como contexto — a posse do material já garante que o aluno só pergunta sobre a sua própria turma."""
    material = await _obter_material_do_educando(db, tenant_id, utilizador, aluno_id, dados.material_id)
    nome_objetivo = None
    if material.objetivo_aprendizagem_id:
        nome_objetivo = (await db.execute(
            select(ObjetivoAprendizagem.nome).where(ObjetivoAprendizagem.id == material.objetivo_aprendizagem_id)
        )).scalar_one_or_none()

    return await perguntar_prof_virtual(
        titulo_material=material.titulo,
        corpo_material=material.corpo,
        nome_objetivo=nome_objetivo,
        historico=dados.historico,
        pergunta=dados.pergunta
    )


# ==========================================
# G. EXAMES ONLINE (LMS) DO EDUCANDO
# ==========================================
async def _obter_matricula_ativa_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> Matricula:
    """Mesma posse+matrícula-ativa já usada em materiais/tarefas, mas aqui levanta 404 em vez de devolver lista vazia — fazer exame exige mesmo ter turma atual."""
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        raise HTTPException(status_code=404, detail="Educando sem matrícula ativa.")
    return matricula


def _garantir_e_aluno(utilizador: dict):
    """Ver/consultar resultados é aberto a ALUNO e RESPONSAVEL (como o resto do Portal) — mas fazer o exame em si (iniciar/submeter) é só do próprio aluno, nunca do encarregado de educação."""
    if utilizador["perfil_acesso"] != "ALUNO":
        raise HTTPException(status_code=403, detail="Só o próprio aluno pode realizar o exame.")


async def listar_exames_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID) -> list[dict]:
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula or matricula.status_matricula != "ATIVO":
        return []
    return await crud_lms.listar_exames_do_aluno(db, tenant_id, matricula.id, matricula.turma_id)


async def iniciar_tentativa_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, exame_id: uuid.UUID) -> dict:
    _garantir_e_aluno(utilizador)
    matricula = await _obter_matricula_ativa_do_educando(db, tenant_id, utilizador, aluno_id)
    return await crud_lms.iniciar_tentativa(db, tenant_id, matricula.id, matricula.turma_id, exame_id)


async def submeter_tentativa_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, exame_id: uuid.UUID, dados: LMSSubmeterTentativa) -> dict:
    _garantir_e_aluno(utilizador)
    matricula = await _obter_matricula_ativa_do_educando(db, tenant_id, utilizador, aluno_id)
    return await crud_lms.submeter_tentativa(db, tenant_id, matricula.id, matricula.turma_id, exame_id, dados)


async def registar_evento_suspeito_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, exame_id: uuid.UUID) -> int:
    """Proctoring básico: o aluno saiu da aba durante a tentativa (ver core/utils Page Visibility no frontend)."""
    _garantir_e_aluno(utilizador)
    matricula = await _obter_matricula_ativa_do_educando(db, tenant_id, utilizador, aluno_id)
    return await crud_lms.registar_evento_suspeito(db, tenant_id, matricula.id, matricula.turma_id, exame_id)


async def obter_resultado_tentativa_do_educando(db: AsyncSession, tenant_id, utilizador: dict, aluno_id: uuid.UUID, exame_id: uuid.UUID) -> dict:
    """Resultado + gabarito — aberto a ALUNO e RESPONSAVEL (só leitura, sem restrição extra)."""
    await _garantir_aluno_permitido(db, tenant_id, utilizador, aluno_id)
    matricula = await _obter_matricula_atual(db, tenant_id, aluno_id)
    if not matricula:
        raise HTTPException(status_code=404, detail="Educando sem matrícula.")
    return await crud_lms.obter_resultado_tentativa(db, tenant_id, matricula.id, exame_id)
