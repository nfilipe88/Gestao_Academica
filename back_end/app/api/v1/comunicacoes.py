import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.core.email import enviar_email, template_base
from app.core import fila_notificacoes
from app.schemas.comunicacoes import AnexoComunicacaoOut, ComunicadoCreate
from app.cruds import comunicacoes as crud_comunicacoes

router = APIRouter(prefix="/api/v1/comunicados", tags=["Comunicações"])

# Quem pode enviar comunicados/convocatórias. Professores podem enviar
# (RN pedida), mas não para toda a escola nem para turmas/alunos que não
# são seus — ver validação em crud_comunicacoes._validar_autoria_professor.
_PODE_ENVIAR = exigir_perfil("GESTOR", "SECRETARIA", "PROFESSOR")

# ==========================================
# ROTAS
# ==========================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_comunicado(
    dados: ComunicadoCreate,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ENVIAR)
):
    """Cria e envia (por e-mail, através da fila com retries — ver
    app/core/fila_notificacoes.py) um Comunicado/Convocatória."""
    novo_comunicado, emails = await crud_comunicacoes.criar_comunicado(db, utilizador, dados)

    rotulo_tipo = "Convocatória" if dados.tipo == "CONVOCATORIA" else "Comunicado"
    corpo_html_email = dados.corpo.replace("\n", "<br>")
    for email in emails:
        await fila_notificacoes.agendar_email(
            enviar_email,
            destinatario=email,
            assunto=f"[{rotulo_tipo}] {dados.titulo}",
            corpo_html=template_base(dados.titulo, corpo_html_email)
        )

    return novo_comunicado

@router.get("")
async def listar_comunicados(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    """Lista o histórico de comunicados/convocatórias enviados pela escola, paginado."""
    return await crud_comunicacoes.listar_comunicados(db, utilizador["tenant_id"], page, page_size)


# ==========================================
# ANEXOS
# ==========================================
# NOTA: o anexo fica disponível para download por qualquer staff (via
# plataforma), mas NÃO é incluído automaticamente no e-mail já disparado
# na criação do comunicado (esse envio é imediato, ver acima) — é
# um registo/arquivo do que foi comunicado, não (ainda) um "PDF em
# anexo no e-mail do encarregado". Ver nota na Fase 4 do plano.
@router.put("/{comunicado_id}/anexo", response_model=AnexoComunicacaoOut)
async def anexar_ficheiro(
    comunicado_id: uuid.UUID,
    ficheiro: UploadFile = File(...),
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ENVIAR)
):
    conteudo = await ficheiro.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    return await crud_comunicacoes.adicionar_anexo(
        db, utilizador["tenant_id"], comunicado_id,
        ficheiro.filename or "anexo", ficheiro.content_type or "application/octet-stream", conteudo
    )


@router.get("/{comunicado_id}/anexo")
async def descarregar_anexo(
    comunicado_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(exigir_perfil_staff)
):
    conteudo, content_type, nome_original = await crud_comunicacoes.obter_anexo_conteudo(db, utilizador["tenant_id"], comunicado_id)
    return Response(
        content=conteudo, media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{nome_original}"'}
    )
