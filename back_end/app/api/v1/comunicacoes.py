from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.database.session import obter_sessao_db
from app.database.models import Usuario
from app.database.models_academico import Turma
from app.database.models_pessoas import Aluno, AlunoResponsavel, Professor, ResponsavelFinanceiroLegal
from app.database.models_matricula import Matricula
from app.database.models_comunicacoes import Comunicado
from app.database.models_diario import ProfessorTurmaDisciplina
from app.core.security import obter_utilizador_atual, exigir_perfil
from app.core.email import enviar_email, template_base

router = APIRouter(prefix="/api/v1/comunicados", tags=["Comunicações"])

# Quem pode enviar comunicados/convocatórias. Professores podem enviar
# (RN pedida), mas não para toda a escola nem para turmas/alunos que não
# são seus — ver validação em criar_comunicado (_validar_autoria_professor).
_PODE_ENVIAR = exigir_perfil("GESTOR", "SECRETARIA", "PROFESSOR")


async def _validar_autoria_professor(
    db: AsyncSession, utilizador: dict, destinatario_tipo: str,
    turma_id: uuid.UUID | None, aluno_id: uuid.UUID | None
) -> None:
    """
    Um Professor só pode comunicar com turmas/alunos das turmas onde
    está efetivamente alocado (Professor_Turma_Disciplina — Nível 1).
    Gestor/Secretaria não passam por aqui (já filtrados antes de chamar isto).
    """
    professor = (await db.execute(
        select(Professor).where(
            Professor.usuario_id == utilizador["usuario_id"],
            Professor.tenant_id == utilizador["tenant_id"]
        )
    )).scalars().first()
    if not professor:
        raise HTTPException(status_code=403, detail="Utilizador não corresponde a nenhum professor cadastrado.")

    if destinatario_tipo == "TURMA":
        alocado = (await db.execute(
            select(ProfessorTurmaDisciplina).where(
                ProfessorTurmaDisciplina.professor_id == professor.id,
                ProfessorTurmaDisciplina.turma_id == turma_id
            )
        )).scalars().first()
        if not alocado:
            raise HTTPException(status_code=403, detail="Só pode comunicar com turmas onde lecciona.")

    elif destinatario_tipo == "ALUNO":
        turma_do_aluno = (await db.execute(
            select(Matricula.turma_id).where(
                Matricula.aluno_id == aluno_id,
                Matricula.status_matricula == "ATIVO",
                Matricula.tenant_id == utilizador["tenant_id"]
            )
        )).scalars().all()
        if not turma_do_aluno:
            raise HTTPException(status_code=403, detail="Aluno sem matrícula ativa nesta instituição.")

        alocado = (await db.execute(
            select(ProfessorTurmaDisciplina).where(
                ProfessorTurmaDisciplina.professor_id == professor.id,
                ProfessorTurmaDisciplina.turma_id.in_(turma_do_aluno)
            )
        )).scalars().first()
        if not alocado:
            raise HTTPException(status_code=403, detail="Só pode comunicar com alunos das turmas onde lecciona.")

TIPOS_VALIDOS = {"COMUNICADO", "CONVOCATORIA"}
DESTINATARIOS_VALIDOS = {"TURMA", "ALUNO", "ESCOLA"}

# ==========================================
# SCHEMAS (Pydantic)
# ==========================================
class ComunicadoCreate(BaseModel):
    tipo: str
    titulo: str
    corpo: str
    destinatario_tipo: str
    destinatario_turma_id: uuid.UUID | None = None
    destinatario_aluno_id: uuid.UUID | None = None

# ==========================================
# RESOLUÇÃO DE DESTINATÁRIOS
# ==========================================
async def _resolver_emails_destinatarios(
    db: AsyncSession,
    tenant_id,
    destinatario_tipo: str,
    turma_id: uuid.UUID | None,
    aluno_id: uuid.UUID | None
) -> list[str]:
    """
    Traduz "para quem" (Turma/Aluno/Escola) numa lista de e-mails reais.
    Só responsáveis com e-mail preenchido recebem (é opcional no cadastro).
    """
    emails: set[str] = set()

    if destinatario_tipo == "ALUNO":
        resultado = await db.execute(
            select(ResponsavelFinanceiroLegal.email)
            .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
            .where(
                AlunoResponsavel.aluno_id == aluno_id,
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.email.isnot(None)
            )
        )
        emails.update(email for (email,) in resultado.all())

    elif destinatario_tipo == "TURMA":
        # Só os responsáveis de alunos com matrícula ATIVA na turma.
        resultado = await db.execute(
            select(ResponsavelFinanceiroLegal.email)
            .join(AlunoResponsavel, AlunoResponsavel.responsavel_id == ResponsavelFinanceiroLegal.id)
            .join(Matricula, Matricula.aluno_id == AlunoResponsavel.aluno_id)
            .where(
                Matricula.turma_id == turma_id,
                Matricula.status_matricula == "ATIVO",
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.email.isnot(None)
            )
        )
        emails.update(email for (email,) in resultado.all())

    elif destinatario_tipo == "ESCOLA":
        responsaveis = await db.execute(
            select(ResponsavelFinanceiroLegal.email).where(
                ResponsavelFinanceiroLegal.tenant_id == tenant_id,
                ResponsavelFinanceiroLegal.email.isnot(None)
            )
        )
        emails.update(email for (email,) in responsaveis.all())

        professores = await db.execute(
            select(Usuario.email)
            .join(Professor, Professor.usuario_id == Usuario.id)
            .where(Professor.tenant_id == tenant_id)
        )
        emails.update(email for (email,) in professores.all())

    return list(emails)

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
    if dados.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use um de: {', '.join(sorted(TIPOS_VALIDOS))}.")
    if dados.destinatario_tipo not in DESTINATARIOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Destinatário inválido. Use um de: {', '.join(sorted(DESTINATARIOS_VALIDOS))}.")

    # RBAC adicional: Professor não pode fazer um comunicado institucional
    # para a escola inteira (isso fica para Gestor/Secretaria).
    if utilizador["perfil_acesso"] == "PROFESSOR" and dados.destinatario_tipo == "ESCOLA":
        raise HTTPException(status_code=403, detail="Professores não podem enviar comunicados para toda a escola.")

    tenant_id = utilizador["tenant_id"]

    if dados.destinatario_tipo == "TURMA":
        if not dados.destinatario_turma_id:
            raise HTTPException(status_code=400, detail="Selecione a turma destinatária.")
        turma = (await db.execute(
            select(Turma).where(Turma.id == dados.destinatario_turma_id, Turma.tenant_id == tenant_id)
        )).scalars().first()
        if not turma:
            raise HTTPException(status_code=404, detail="Turma não encontrada na sua instituição.")

    if dados.destinatario_tipo == "ALUNO":
        if not dados.destinatario_aluno_id:
            raise HTTPException(status_code=400, detail="Selecione o aluno destinatário.")
        aluno = (await db.execute(
            select(Aluno).where(Aluno.id == dados.destinatario_aluno_id, Aluno.tenant_id == tenant_id)
        )).scalars().first()
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado na sua instituição.")

    if utilizador["perfil_acesso"] == "PROFESSOR":
        await _validar_autoria_professor(
            db, utilizador, dados.destinatario_tipo, dados.destinatario_turma_id, dados.destinatario_aluno_id
        )

    emails = await _resolver_emails_destinatarios(
        db, tenant_id, dados.destinatario_tipo, dados.destinatario_turma_id, dados.destinatario_aluno_id
    )

    novo_comunicado = Comunicado(
        tenant_id=tenant_id,
        autor_id=utilizador["usuario_id"],
        tipo=dados.tipo,
        titulo=dados.titulo,
        corpo=dados.corpo,
        destinatario_tipo=dados.destinatario_tipo,
        destinatario_turma_id=dados.destinatario_turma_id,
        destinatario_aluno_id=dados.destinatario_aluno_id,
        total_destinatarios=len(emails)
    )
    db.add(novo_comunicado)
    await db.commit()
    await db.refresh(novo_comunicado)

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
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(obter_utilizador_atual)
):
    """Lista o histórico de comunicados/convocatórias enviados pela escola."""
    resultado = await db.execute(
        select(Comunicado, Usuario.nome_completo)
        .outerjoin(Usuario, Usuario.id == Comunicado.autor_id)
        .where(Comunicado.tenant_id == utilizador["tenant_id"])
        .order_by(Comunicado.data_envio.desc())
    )
    return [
        {
            "id": comunicado.id,
            "autor_nome": autor_nome or "—",
            "tipo": comunicado.tipo,
            "titulo": comunicado.titulo,
            "corpo": comunicado.corpo,
            "destinatario_tipo": comunicado.destinatario_tipo,
            "destinatario_turma_id": comunicado.destinatario_turma_id,
            "destinatario_aluno_id": comunicado.destinatario_aluno_id,
            "total_destinatarios": comunicado.total_destinatarios,
            "data_envio": comunicado.data_envio,
        }
        for comunicado, autor_nome in resultado.all()
    ]
