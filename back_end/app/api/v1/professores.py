from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field

from app.database.session import obter_sessao_db
from app.database.models import Usuario
from app.database.models_pessoas import Professor
from app.core.security import obter_utilizador_atual, exigir_perfil, gerar_hash_senha
from app.core.email import enviar_email, template_base

router = APIRouter(prefix="/api/v1/professores", tags=["Professores"])

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class ProfessorCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    palavra_passe: str = Field(..., min_length=8)
    formacao_academica: str | None = None

# ==========================================
# ROTAS
# ==========================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def criar_professor(
    dados: ProfessorCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(obter_sessao_db),
    # Só o Gestor pode criar contas de Professor (RBAC).
    utilizador: dict = Depends(exigir_perfil("GESTOR"))
):
    """
    Cria a conta de Professor: um Usuario novo (perfil_acesso=PROFESSOR,
    com login próprio) e o registo de Professor associado, numa única
    transação — ou cria tudo, ou reverte tudo.
    """
    tenant_id = utilizador["tenant_id"]

    email_existente = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if email_existente.scalars().first():
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    try:
        novo_usuario = Usuario(
            tenant_id=tenant_id,
            nome_completo=dados.nome_completo,
            email=dados.email,
            senha_hash=gerar_hash_senha(dados.palavra_passe),
            perfil_acesso="PROFESSOR"
        )
        db.add(novo_usuario)
        await db.flush() # Obter o id do Usuario sem fazer commit final

        novo_professor = Professor(
            tenant_id=tenant_id,
            usuario_id=novo_usuario.id,
            formacao_academica=dados.formacao_academica
        )
        db.add(novo_professor)
        await db.commit()
        await db.refresh(novo_professor)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar professor: {str(e)}")

    background_tasks.add_task(
        enviar_email,
        destinatario=dados.email,
        assunto="A sua conta de Professor foi criada",
        corpo_html=template_base(
            "Bem-vindo(a) à equipa docente!",
            f"""
            <p>Olá {dados.nome_completo},</p>
            <p>Foi criada uma conta de Professor para si na plataforma de Gestão Académica.</p>
            <p>Já pode iniciar sessão com o e-mail <strong>{dados.email}</strong> e a
            palavra-passe definida no momento do registo.</p>
            """
        )
    )

    return {
        "id": novo_professor.id,
        "usuario_id": novo_usuario.id,
        "nome_completo": dados.nome_completo,
        "email": dados.email,
        "formacao_academica": dados.formacao_academica,
        "data_criacao": novo_professor.data_criacao,
    }

@router.get("")
async def listar_professores(
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista os professores da escola do utilizador logado."""
    resultado = await db.execute(
        select(Professor, Usuario.nome_completo, Usuario.email)
        .join(Usuario, Usuario.id == Professor.usuario_id)
        .where(Professor.tenant_id == utilizador["tenant_id"])
    )
    return [
        {
            "id": professor.id,
            "usuario_id": professor.usuario_id,
            "nome_completo": nome_completo,
            "email": email,
            "formacao_academica": professor.formacao_academica,
            "data_criacao": professor.data_criacao,
        }
        for professor, nome_completo, email in resultado.all()
    ]
