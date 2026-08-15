from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import obter_sessao_db
from app.core.security import exigir_perfil, exigir_perfil_staff
from app.core.email import enviar_email, template_base
from app.schemas.comunicacoes import ComunicadoCreate
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_ENVIAR)
):
    """Cria e envia (por e-mail, em background) um Comunicado/Convocatória."""
    novo_comunicado, emails = await crud_comunicacoes.criar_comunicado(db, utilizador, dados)

    rotulo_tipo = "Convocatória" if dados.tipo == "CONVOCATORIA" else "Comunicado"
    corpo_html_email = dados.corpo.replace("\n", "<br>")
    for email in emails:
        background_tasks.add_task(
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
