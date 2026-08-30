import uuid
from datetime import date, datetime, time
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Time, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base

class ProfessorTurmaDisciplina(Base):
    """Alocação de docentes: define que um Professor lecciona uma
    Disciplina numa Turma. É a base do Diário de Classe — RN01 exige
    validar que quem lança notas/faltas é realmente o professor alocado.
    """
    __tablename__ = "professor_turma_disciplina"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    professor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professor.id", ondelete="CASCADE"), nullable=False)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("professor_id", "turma_id", "disciplina_id", name="uq_alocacao_professor_turma_disciplina"),
    )

class RegistroFrequencia(Base):
    """Diário - Chamada. Um registo por aluno, por disciplina, por dia de aula."""
    __tablename__ = "registro_frequencia"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    data_aula: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade_aulas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    conteudo_programado: Mapped[str] = mapped_column(String(500), nullable=True)
    presenca: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    faltas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Um só registo por aluno/disciplina/dia — lançar de novo faz upsert.
        UniqueConstraint("matricula_id", "disciplina_id", "data_aula", name="uq_frequencia_matricula_disciplina_data"),
    )

class RegistroNota(Base):
    """Diário - Avaliação. Uma nota por aluno, disciplina e período de avaliação.

    Desde a introdução de Avaliacao/NotaAvaliacao, esta nota passa a
    poder ser CALCULADA automaticamente (média ponderada pelas
    avaliações — provas/contínuas — lançadas nesse período) em vez de
    escrita à mão. `calculada_automaticamente` distingue as duas
    origens: quando True, o valor é mantido em sincronia por
    cruds/diario.py::_recalcular_nota_periodo e o lançamento manual
    direto (lancar_notas_lote) passa a ser recusado para esta
    combinação matrícula/disciplina/período — ver
    _validar_sem_avaliacoes. Registos antigos (anteriores a esta
    funcionalidade) ficam com False e continuam editáveis à mão como
    sempre foram.
    """
    __tablename__ = "registro_nota"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    periodo_avaliacao: Mapped[str] = mapped_column(String(50), nullable=False) # Ex: "1º Bimestre"
    tipo_avaliacao: Mapped[str] = mapped_column(String(50), nullable=True) # Ex: "Prova Escrita"
    data_avaliacao: Mapped[date] = mapped_column(Date, nullable=True)
    valor_nota: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    calculada_automaticamente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Upsert target: relançar a nota do mesmo aluno/disciplina/período atualiza, não duplica.
        UniqueConstraint("matricula_id", "disciplina_id", "periodo_avaliacao", name="uq_nota_matricula_disciplina_periodo"),
    )


class Avaliacao(Base):
    """Uma avaliação concreta (prova ou avaliação contínua) dentro de um
    período, para uma turma+disciplina — ex.: "Teste de Células"
    (PROVA, peso 60) ou "Trabalho de grupo" (CONTINUA, peso 40).

    A nota final do período em RegistroNota passa a ser a média
    ponderada (por `peso`) de todas as Avaliacao com nota lançada
    nesse período — ver cruds/diario.py::_recalcular_nota_periodo.

    Agendamento (hora_inicio/hora_fim/sala/data_limite_correcao): só
    preenchido quando o TipoAvaliacaoConfig do tenant marca este
    tipo_avaliacao como requer_agendamento=True — nesse caso só
    Gestor/Secretaria pode criar/editar esta Avaliacao (ver RN01 em
    cruds/diario.py::_validar_agendamento). Para tipos sem essa flag
    (ex.: avaliação contínua do dia-a-dia), estes campos ficam vazios
    e o professor continua a criar livremente na sua alocação, como
    sempre foi.

    grupo_agendamento_id: partilhado por todas as Avaliacao criadas
    de uma vez pelo agendamento "Geral" (toda a escola) — não é FK,
    só serve para o frontend agrupar visualmente linhas irmãs; cada
    uma continua a ser uma Avaliacao independente (o professor de
    cada turma lança a sua nota separadamente).
    """
    __tablename__ = "avaliacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    turma_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)

    periodo_avaliacao: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)  # Ex: "Teste de Células"
    # Nome de um TipoAvaliacaoConfig do tenant (texto, não FK — mesmo
    # padrão de outros campos "status" nesta base de dados). Por isso
    # o crud de TipoAvaliacaoConfig impede renomear um tipo já usado
    # por alguma Avaliacao (ver cruds/configuracoes.py::atualizar_tipo_avaliacao).
    tipo_avaliacao: Mapped[str] = mapped_column(String(50), nullable=False)
    peso: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=100)  # peso relativo dentro do período — não precisa somar 100 (normalizado no cálculo)
    data_avaliacao: Mapped[date | None] = mapped_column(Date, nullable=True)

    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fim: Mapped[time | None] = mapped_column(Time, nullable=True)
    sala: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_limite_correcao: Mapped[date | None] = mapped_column(Date, nullable=True)
    grupo_agendamento_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    # Opcional: a que tópico do currículo esta avaliação corresponde
    # (ex.: "Células"). Sem isto a avaliação continua a contar para a
    # nota final do período normalmente — só fica de fora do relatório
    # de eficiência por objetivo em Indicadores.
    objetivo_aprendizagem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("objetivo_aprendizagem.id", ondelete="SET NULL"), nullable=True
    )

    criado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class TipoAvaliacaoConfig(Base):
    """Catálogo de tipos de avaliação por escola (ex.: "Contínua", "Prova",
    "Exame Final", "Trabalho de Grupo") — substitui a lista fixa
    anterior (CONTINUA/PROVA), que agora só serve de seed inicial (ver
    migração). `requer_agendamento` é o que decide o RBAC de
    Avaliacao: tipos marcados assim só podem ser criados/editados por
    Gestor/Secretaria, com data/hora obrigatórias (ver
    cruds/diario.py::_validar_agendamento).
    """
    __tablename__ = "tipo_avaliacao_config"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    nome: Mapped[str] = mapped_column(String(50), nullable=False)
    requer_agendamento: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_tipo_avaliacao_tenant_nome"),
    )


class NotaAvaliacao(Base):
    """Nota de um aluno numa Avaliacao concreta. Sempre que uma linha
    aqui é criada/alterada/apagada, a nota final do período
    (RegistroNota) desse aluno é recalculada — ver
    cruds/diario.py::_recalcular_nota_periodo.
    """
    __tablename__ = "nota_avaliacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    avaliacao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("avaliacao.id", ondelete="CASCADE"), nullable=False)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False)

    valor_nota: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        # Upsert target: relançar a nota do mesmo aluno na mesma avaliação atualiza, não duplica.
        UniqueConstraint("avaliacao_id", "matricula_id", name="uq_nota_avaliacao_matricula"),
    )

class PeriodoAvaliacao(Base):
    """
    RN03 do Diário de Classe: "janela de lançamento". A secretaria
    define prazos (ex: "1º Bimestre fecha dia 30/04") — enquanto
    aberto=True, lançar notas nesse periodo_avaliacao é permitido;
    depois de trancado, POST .../notas/lote passa a devolver 403.

    Não é obrigatório existir um registo aqui para cada
    periodo_avaliacao usado em RegistroNota — o documento não define
    isto como pré-requisito, só como algo que a secretaria PODE
    trancar. Por isso um nome sem registo correspondente aqui
    continua livre (comportamento anterior a esta funcionalidade,
    preservado para não quebrar o fluxo já existente).
    """
    __tablename__ = "periodo_avaliacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)

    nome: Mapped[str] = mapped_column(String(50), nullable=False)  # tem de bater certo com RegistroNota.periodo_avaliacao
    aberto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_fecho: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_periodo_avaliacao_tenant_nome"),
    )


class RegistroNotaAuditoria(Base):
    """RN04: sempre que uma nota já existente é alterada, fica aqui o rasto
    (quem alterou, quando, valor antigo e novo) — não é criado no primeiro
    lançamento, só nas alterações seguintes.
    """
    __tablename__ = "registro_nota_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    registro_nota_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("registro_nota.id", ondelete="CASCADE"), nullable=False)
    alterado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    valor_antigo: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    valor_novo: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    alterado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class RegistroComportamento(Base):
    """Incidente ou nota de comportamento de um aluno — positivo (elogio,
    destaque) ou negativo (advertência, infração) — complementar às
    notas/frequência académicas (Nível 1 do Diário de Classe, mesmo
    módulo comercial — ver app/core/modulos.py).

    Fica ligado à Matrícula (não só ao Aluno), como RegistroNota/
    RegistroFrequencia: é o percurso NESTE ano letivo/turma que
    interessa mostrar, mesmo raciocínio de sempre nesta plataforma.
    disciplina_id é opcional — regista o contexto quando o incidente
    aconteceu numa aula em concreto, mas Gestor/Secretaria também
    registam comportamento fora de qualquer disciplina (ex.: no
    recreio, na entrada).
    """
    __tablename__ = "registro_comportamento"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    matricula_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"), nullable=False, index=True)
    disciplina_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplina.id", ondelete="SET NULL"), nullable=True)
    registrado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # POSITIVO, NEGATIVO
    descricao: Mapped[str] = mapped_column(String(1000), nullable=False)
    data_ocorrencia: Mapped[date] = mapped_column(Date, nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
