"""LMS: materiais de aula publicados pelo professor (por turma+disciplina)
e o motor de exames online (banco de questões + exames com baralhamento
+ tentativas corrigidas automaticamente).

MaterialAula é o conteúdo sobre o qual o aluno pode pedir ajuda ao
Prof. Virtual (ver app/core/prof_virtual.py) — o botão de ajuda vive
sempre "dentro" de um material, nunca solto, para a IA ter contexto
real do que o aluno está a estudar.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class MaterialAula(Base):
    __tablename__ = "material_aula"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)  # Ex: "Equações do 2º Grau"
    corpo: Mapped[str] = mapped_column(Text, nullable=False)  # conteúdo em texto simples — sem anexos/multimédia nesta primeira versão

    # Opcional: liga ao catálogo de Fase 2 (ver models_academico.py) —
    # dá ao Prof. Virtual e ao relatório de Indicadores um vocabulário
    # comum para o mesmo tópico.
    objetivo_aprendizagem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objetivo_aprendizagem.id", ondelete="SET NULL"), nullable=True
    )

    publicado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # False = rascunho, aluno não vê

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))


class LMSQuestao(Base):
    """Um item do banco de questões, por disciplina — reutilizável em
    vários exames (ver LMSExameQuestao). Só dois tipos suportados nesta
    primeira versão, os únicos com correção automática sem ambiguidade
    (resposta aberta ficaria por corrigir manualmente, fora de alcance
    aqui — ver nota em MaterialAula.corpo sobre a falta de anexos)."""
    __tablename__ = "lms_questao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # ESCOLHA_MULTIPLA, VERDADEIRO_FALSO
    opcoes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # só ESCOLHA_MULTIPLA — vazio em VERDADEIRO_FALSO
    # ESCOLHA_MULTIPLA: índice (como string, ex. "0") da opção certa em `opcoes`.
    # VERDADEIRO_FALSO: literalmente "VERDADEIRO" ou "FALSO".
    resposta_correta: Mapped[str] = mapped_column(String(500), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("1.00"))

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class LMSExame(Base):
    """Um exame online agendado para uma alocação (turma+disciplina de
    um professor) — motor de exames com janela temporal, duração por
    tentativa e baralhamento de perguntas. Distinto de Avaliacao
    (Diário de Classe), que é uma nota manual/presencial lançada pelo
    professor; aqui a correção é sempre automática (ver LMSTentativaExame).

    Liga-se a Professor_Turma_Disciplina, nunca duplica turma_id/
    disciplina_id diretamente — mesmo princípio já usado em Horários e
    em Tarefa.
    """
    __tablename__ = "lms_exame"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    alocacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professor_turma_disciplina.id", ondelete="CASCADE"), nullable=False)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_fim: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duracao_minutos: Mapped[int] = mapped_column(Integer, nullable=False)  # tempo máximo por tentativa, independente da largura da janela data_inicio/data_fim
    baralhar_perguntas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    publicado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # False = rascunho — aluno não vê nem pode iniciar

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class LMSExameQuestao(Base):
    """Associa Questões do banco a um Exame concreto, com a ordem por
    omissão (só usada quando Exame.baralhar_perguntas=False — caso
    contrário cada aluno recebe a sua própria ordem, gravada em
    LMSTentativaExame.ordem_questoes)."""
    __tablename__ = "lms_exame_questao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    exame_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lms_exame.id", ondelete="CASCADE"), nullable=False)
    questao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lms_questao.id", ondelete="CASCADE"), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("exame_id", "questao_id", name="uq_lms_exame_questao_exame_questao"),
        UniqueConstraint("exame_id", "ordem", name="uq_lms_exame_questao_exame_ordem"),
    )


class LMSTentativaExame(Base):
    """Uma tentativa de um aluno a um Exame — nasce ao clicar "Começar"
    (ordem_questoes fixa a ordem apresentada a ESTE aluno, já baralhada
    se aplicável) e fecha ao submeter. Corrigida automaticamente — só
    ESCOLHA_MULTIPLA/VERDADEIRO_FALSO, sem intervenção do professor.

    eventos_suspeitos: reservado para o proctoring básico (Page
    Visibility API) — contagem de vezes que o aluno saiu da aba
    durante a tentativa. Existe já aqui para não precisar de outra
    migração quando essa funcionalidade for ligada.
    """
    __tablename__ = "lms_tentativa_exame"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    exame_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lms_exame.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)

    ordem_questoes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # ids das questões (str), na ordem apresentada a este aluno
    respostas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {questao_id (str): resposta dada (str)}
    nota_obtida: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    nota_maxima: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    eventos_suspeitos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_submissao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Uma tentativa por aluno por exame nesta primeira versão — sem
        # reentrada automática (o professor teria de apagar a tentativa
        # à mão para permitir repetir, o que não expomos ainda na API).
        UniqueConstraint("exame_id", "matricula_id", name="uq_lms_tentativa_exame_exame_matricula"),
    )
