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
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
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
    vários exames (ver LMSExameQuestao). ESCOLHA_MULTIPLA/VERDADEIRO_FALSO
    têm correção automática sem ambiguidade (comparação de string com
    resposta_correta — ver cruds/lms.py::submeter_tentativa). ABERTA
    (resposta de texto livre) não tem correção automática — fica a
    aguardar um professor/staff atribuir pontos manualmente (ver
    cruds/lms.py::corrigir_tentativa e LMSTentativaExame.corrigida_finalizada)."""
    __tablename__ = "lms_questao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # ESCOLHA_MULTIPLA, VERDADEIRO_FALSO, ABERTA
    opcoes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # só ESCOLHA_MULTIPLA — vazio em VERDADEIRO_FALSO/ABERTA
    # ESCOLHA_MULTIPLA: índice (como string, ex. "0") da opção certa em `opcoes`.
    # VERDADEIRO_FALSO: literalmente "VERDADEIRO" ou "FALSO".
    # ABERTA: opcional — dica de correção só visível ao staff (nunca ao
    # aluno), não usada em nenhuma comparação automática; pode ficar vazia.
    resposta_correta: Mapped[str] = mapped_column(String(500), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("1.00"))

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class LMSExame(Base):
    """Uma VARIANTE de um exame online (grupo_id agrupa as variantes
    irmãs de uma mesma prova — "Variante A/B/C" com perguntas
    genuinamente diferentes, não só ordem baralhada) agendada para uma
    alocação (turma+disciplina de um professor) — motor de exames com
    janela temporal, duração por tentativa e baralhamento de perguntas.
    Distinto de Avaliacao (Diário de Classe), que é uma nota manual/
    presencial lançada pelo professor; aqui a correção é automática
    para questões objetivas e manual (professor/staff) para questões
    ABERTA ou quando alguém decide sobrescrever o total, ex. prova
    presencial (ver LMSTentativaExame.corrigida_finalizada e
    cruds/lms.py::corrigir_tentativa) — mas, através de avaliacao_id,
    o resultado passa a alimentar a mesma Avaliacao/NotaAvaliacao do
    Diário só depois de finalizado (ver cruds/lms.py::submeter_tentativa).

    Liga-se a Professor_Turma_Disciplina, nunca duplica turma_id/
    disciplina_id diretamente — mesmo princípio já usado em Horários e
    em Tarefa.

    grupo_id NÃO é uma FK — é uma chave partilhada entre as variantes
    irmãs de uma mesma prova, sempre preenchida mesmo quando só há uma
    variante (mesmo padrão não-FK de Avaliacao.grupo_agendamento_id,
    usado por cruds/diario.py::agendar_avaliacao_geral). publicado e
    iniciado são condições distintas e AMBAS necessárias para um aluno
    poder começar (ver cruds/lms.py::_obter_exame_publicado_da_turma):
    publicado é preparado pelo professor (ou pela rota .../publicar,
    que continua aberta a qualquer staff mas fica inofensiva sozinha);
    iniciado só é ligado pelo Gestor/Secretaria via
    cruds/lms.py::iniciar_grupo_exame, o único momento em que a
    distribuição por variantes (LMSGrupoExameAtribuicao) é gerada.
    """
    __tablename__ = "lms_exame"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    alocacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professor_turma_disciplina.id", ondelete="CASCADE"), nullable=False)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_fim: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duracao_minutos: Mapped[int] = mapped_column(Integer, nullable=False)  # tempo máximo por tentativa, independente da largura da janela data_inicio/data_fim
    baralhar_perguntas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    publicado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # False = rascunho — aluno não vê nem pode iniciar

    grupo_id: Mapped[uuid.UUID] = mapped_column(nullable=False, default=uuid.uuid4, index=True)
    letra_variante: Mapped[str] = mapped_column(String(5), nullable=False, default="A")
    modalidade: Mapped[str] = mapped_column(String(20), nullable=False, default="PRESENCIAL")  # PRESENCIAL | REMOTO — só informativo
    # RESTRICT (não CASCADE): uma Avaliação já usada para notas de um
    # exame LMS nunca deve desaparecer silenciosamente por uma cascata
    # vinda do lado do Diário — ver cruds/diario.py::apagar_avaliacao.
    # Nullable: exames criados antes desta funcionalidade (ou, no
    # futuro, um caminho sem avaliação associada) continuam a corrigir
    # automaticamente sem alimentar nenhum período — ver
    # cruds/lms.py::submeter_tentativa.
    avaliacao_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("avaliacao.id", ondelete="RESTRICT"), nullable=True)
    iniciado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    iniciado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class LMSExameQuestao(Base):
    """Associa Questões do banco a um Exame concreto, com a ordem por
    omissão (só usada quando Exame.baralhar_perguntas=False — caso
    contrário cada aluno recebe a sua própria ordem, gravada em
    LMSTentativaExame.ordem_questoes)."""
    __tablename__ = "lms_exame_questao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
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
    se aplicável) e fecha ao submeter.

    Sem coluna de estado própria — o estado continua totalmente
    derivado (mesmo princípio de sempre), agora com 3 valores em vez
    de 2: data_submissao vazia = EM_CURSO/NAO_INICIADA; preenchida e
    corrigida_finalizada=False = AGUARDA_CORRECAO (há pelo menos uma
    questão ABERTA por pontuar); preenchida e corrigida_finalizada=True
    = SUBMETIDA (cobre tanto "sempre foi 100% automática", o caso de
    sempre, como "finalizada manualmente" — ver
    cruds/lms.py::corrigir_tentativa).

    correcoes_manuais é JSON, não uma tabela própria — mesmo princípio
    de `respostas`: escrito/lido inteiro por tentativa, nunca
    interrogado linha-a-linha em SQL. Formato:
    {questao_id (str): {"pontos": "1.50", "comentario": str | None}}.

    eventos_suspeitos: reservado para o proctoring básico (Page
    Visibility API) — contagem de vezes que o aluno saiu da aba
    durante a tentativa. Existe já aqui para não precisar de outra
    migração quando essa funcionalidade for ligada.
    """
    __tablename__ = "lms_tentativa_exame"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    exame_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lms_exame.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)

    ordem_questoes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # ids das questões (str), na ordem apresentada a este aluno
    respostas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {questao_id (str): resposta dada (str)}
    nota_obtida: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    nota_maxima: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    eventos_suspeitos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # default True: uma tentativa sem nenhuma questão ABERTA fica
    # sempre finalizada de imediato em submeter_tentativa, exatamente
    # como antes desta funcionalidade existir (retrocompatibilidade
    # total das linhas já existentes, ver migração).
    corrigida_finalizada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    correcoes_manuais: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    corrigido_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    corrigido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_submissao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Uma tentativa por aluno por exame nesta primeira versão — sem
        # reentrada automática (o professor teria de apagar a tentativa
        # à mão para permitir repetir, o que não expomos ainda na API).
        UniqueConstraint("exame_id", "matricula_id", name="uq_lms_tentativa_exame_exame_matricula"),
    )


class LMSGrupoExameAtribuicao(Base):
    """Atribuição de um aluno a UMA variante (LMSExame) dentro de um
    grupo de variantes (LMSExame.grupo_id) — criada exatamente uma vez,
    só no momento do INICIAR (ver cruds/lms.py::iniciar_grupo_exame),
    nunca antes. Round-robin automático por omissão;
    atribuido_manualmente=True marca uma reatribuição feita por um
    Gestor depois (ver cruds/lms.py::reatribuir_variante_aluno).
    Resolve "qual variante é a minha" do lado do aluno —
    listar_exames_do_aluno filtra por esta tabela em vez de expor
    todas as variantes irmãs.

    Mesmo padrão de LoteImportacao/LoteImportacaoAluno (uma linha por
    aluno afetado) — aqui o "grupo" é a chave partilhada grupo_id nos
    LMSExame irmãos, não uma tabela cabeçalho própria.
    """
    __tablename__ = "lms_grupo_exame_atribuicao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    grupo_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    exame_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lms_exame.id", ondelete="CASCADE"), nullable=False)

    atribuido_manualmente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    atribuido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    atribuido_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("grupo_id", "matricula_id", name="uq_lms_grupo_atribuicao_matricula"),
    )
