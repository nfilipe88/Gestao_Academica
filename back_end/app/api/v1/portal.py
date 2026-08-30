import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil
from app.cruds import portal as crud_portal
from app.schemas.lms import LMSSubmeterTentativa, ProfVirtualPerguntaCreate
from app.schemas.portal import PedirTransferenciaRequest

router = APIRouter(prefix="/api/v1/portal", tags=["Portal do Aluno/Responsável"])

# Só logins ALUNO/RESPONSAVEL usam este router — Gestor/Secretaria/
# Professor já têm as suas próprias telas (Matrículas, Diário,
# Horários, Financeiro) com visão completa da escola.
_PODE_ACEDER = exigir_perfil("ALUNO", "RESPONSAVEL")


@router.get("/meus-educandos")
async def listar_meus_educandos(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Alunos que este login pode consultar — o próprio (ALUNO) ou os seus educandos (RESPONSAVEL)."""
    return await crud_portal.listar_meus_educandos(db, utilizador["tenant_id"], utilizador)


@router.get("/educandos/{aluno_id}/horario")
async def obter_horario_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Grade horária semanal da turma atual do educando."""
    return await crud_portal.obter_horario_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/boletim")
async def obter_boletim_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Notas e frequência do educando, agrupadas por disciplina."""
    return await crud_portal.obter_boletim_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/financeiro")
async def obter_financeiro_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """
    Contrato e extrato de faturas do educando. Para pagar, o front-end
    chama diretamente POST /financeiro/faturas/{id}/gerar-cobranca e
    /financeiro/transacoes/capturar — já abertos a qualquer autenticado
    e com o mesmo controlo de posse aplicado aqui (ver cruds/financeiro.py).
    """
    return await crud_portal.obter_financeiro_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.post("/educandos/{aluno_id}/pedir-rematricula")
async def pedir_rematricula(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Confirma interesse em renovar a matrícula do educando para o ano
    letivo seguinte — não cria a matrícula em si, só notifica a
    Secretaria/Gestor (que escolhem a turma de destino)."""
    return await crud_portal.pedir_rematricula(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.post("/educandos/{aluno_id}/pedir-transferencia")
async def pedir_transferencia(
    aluno_id: uuid.UUID,
    dados: PedirTransferenciaRequest,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Pede a transferência/reingresso cross-escola do educando para
    outra instituição desta plataforma (identificada pelo NIF) — sujeito
    à mesma aprovação do Super Admin de sempre (ver POST /transferencias)."""
    return await crud_portal.pedir_transferencia(db, utilizador["tenant_id"], utilizador, aluno_id, dados.nif_destino, dados.motivo)


@router.get("/educandos/{aluno_id}/estatisticas")
async def obter_estatisticas_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Aproveitamento (médias, geral e por disciplina) e assiduidade (taxa de presença) do educando."""
    return await crud_portal.obter_estatisticas_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/comunicados")
async def listar_comunicados_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Histórico de comunicados/convocatórias dirigidos ao educando (à sua turma, a ele ou a toda a escola)."""
    return await crud_portal.listar_comunicados_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/comunicados/{comunicado_id}/anexo")
async def obter_anexo_comunicado_do_educando(
    aluno_id: uuid.UUID,
    comunicado_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    conteudo, content_type, nome_original = await crud_portal.obter_anexo_comunicado_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, comunicado_id)
    return Response(
        content=conteudo, media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{nome_original}"'}
    )


@router.get("/educandos/{aluno_id}/tarefas")
async def listar_tarefas_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Trabalhos/tarefas do educando (prazo, status de entrega e nota, quando já avaliado)."""
    return await crud_portal.listar_tarefas_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/materiais")
async def listar_materiais_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Materiais de aula publicados para a turma atual do educando."""
    return await crud_portal.listar_materiais_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.get("/educandos/{aluno_id}/materiais/{material_id}")
async def obter_material_do_educando(
    aluno_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Conteúdo de um material de aula — só se pertencer à turma atual do educando."""
    return await crud_portal.obter_material_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, material_id)


@router.post("/educandos/{aluno_id}/prof-virtual")
async def perguntar_prof_virtual(
    aluno_id: uuid.UUID,
    dados: ProfVirtualPerguntaCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Envia uma pergunta ao Prof. Virtual sobre um material de aula concreto. Devolve a resposta (chat sem persistência — o histórico viaja no pedido)."""
    resposta = await crud_portal.perguntar_prof_virtual_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, dados)
    return {"resposta": resposta}


@router.get("/educandos/{aluno_id}/exames")
async def listar_exames_do_educando(
    aluno_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Exames publicados para a turma atual do educando, com o estado da sua tentativa (se existir)."""
    return await crud_portal.listar_exames_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id)


@router.post("/educandos/{aluno_id}/exames/{exame_id}/iniciar")
async def iniciar_tentativa_exame(
    aluno_id: uuid.UUID,
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Começa (ou retoma) a tentativa do aluno a este exame — nunca do encarregado de educação. Nunca inclui o gabarito."""
    return await crud_portal.iniciar_tentativa_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, exame_id)


@router.post("/educandos/{aluno_id}/exames/{exame_id}/evento-suspeito")
async def registar_evento_suspeito_exame(
    aluno_id: uuid.UUID,
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Proctoring básico: o frontend chama isto quando deteta que o aluno saiu da aba durante a tentativa (Page Visibility API). Nunca bloqueia o exame — só regista para o professor rever."""
    total = await crud_portal.registar_evento_suspeito_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, exame_id)
    return {"eventos_suspeitos": total}


@router.post("/educandos/{aluno_id}/exames/{exame_id}/submeter")
async def submeter_tentativa_exame(
    aluno_id: uuid.UUID,
    exame_id: uuid.UUID,
    dados: LMSSubmeterTentativa,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Submete as respostas — corrigido automaticamente na hora."""
    return await crud_portal.submeter_tentativa_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, exame_id, dados)


@router.get("/educandos/{aluno_id}/exames/{exame_id}/resultado")
async def obter_resultado_exame(
    aluno_id: uuid.UUID,
    exame_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ACEDER)
):
    """Resultado + gabarito completo — só depois de submetida a tentativa."""
    return await crud_portal.obter_resultado_tentativa_do_educando(db, utilizador["tenant_id"], utilizador, aluno_id, exame_id)
