import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import List
from sqlalchemy import Boolean, Date, Integer, Numeric, String, ForeignKey, DateTime, Text, Time, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome_fantasia: Mapped[str] = mapped_column(String(255), nullable=False)
    razao_social: Mapped[str] = mapped_column(String(255), nullable=True)
    nif: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ATIVO")
    # Validade da licença de acesso à plataforma — nullable (sem data
    # definida = sem expiração automática, ex.: o tenant interno da
    # plataforma). Gerido pelo Super Admin; job diário do scheduler
    # alerta a aproximar-se e suspende automaticamente ao expirar (ver
    # app/core/scheduler.py::job_validade_licenca_diaria).
    data_validade_licenca: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Isenção do limite de alunos do plano ativo (PlanoSaaS.limite_alunos),
    # concedida pelo Super Admin — ver app/core/limites_plano.py.
    isento_limite_alunos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Aceitação da Política de Privacidade/Termos no auto-registo — ver
    # app/core/privacidade.py::VERSAO_TERMOS. NULL = escola criada antes
    # deste registo existir, ou pelo Super Admin.
    termos_aceites_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    termos_versao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Configurações da escola (editável pelo próprio GESTOR, ao contrário
    # dos campos acima que são geridos pelo Super Admin) — ver
    # app/api/v1/configuracoes.py. Tudo nullable: uma escola nova não é
    # obrigada a preencher isto antes de poder usar a plataforma.
    iban: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Código ISO 4217 (EUR, USD, ...) — controla a moeda mostrada em toda
    # a plataforma E a moeda enviada ao PayPal nas cobranças (ver
    # app/core/paypal.py). Por isso é restrita, no schema Pydantic, à
    # lista de moedas que o PayPal realmente aceita — nunca um código
    # livre que depois falharia silenciosamente na cobrança.
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR", server_default="EUR")
    telefone_contacto: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email_contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    morada: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pais: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Taxa de matrícula — encargo único (distinto das mensalidades
    # recorrentes) cobrado uma vez por matrícula. NULL = escola não cobra
    # taxa de matrícula nenhuma. Serve de valor por omissão tanto para
    # o contrato financeiro assinado à mão em Financeiro (ver
    # ContratoCreate.valor_taxa_matricula) como para a conversão
    # automática RN01 a partir da candidatura self-service (ver
    # cruds/crm.py::_tentar_matricula_e_contrato_automaticos); em ambos
    # os casos fica gravada como a parcela nº 0 do contrato — reaproveita
    # toda a maquinaria de Fatura_Mensalidade/Transacao_Gateway já
    # existente (cobrança PayPal, régua de cobrança RN04, recibo, RN08
    # de ordem de pagamento) sem precisar de tabelas nem rotas novas.
    valor_taxa_matricula: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Nota mínima de aprovação (escala livre — cada escola usa a sua,
    # ex.: 0-20 ou 0-10) — usada no Boletim/Indicadores para marcar
    # Aprovado/Reprovado. Sem valor definido, essa marcação não aparece.
    nota_minima_aprovacao: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    # Critérios do fecho do ano (app/core/resultados.py): quantas disciplinas
    # o aluno pode ter abaixo da nota mínima e ainda ser APROVADO (0 = tem de
    # passar a todas) e, opcionalmente, o limite de faltas (% das aulas
    # lecionadas) a partir do qual reprova por faltas (nulo = não se aplica).
    max_disciplinas_reprovadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    limite_faltas_percentagem: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # Abrir/encerrar as inscrições de AUTOATENDIMENTO: candidatura pública de
    # matrícula e pedido de rematrícula no Portal. A Secretaria/Gestor
    # continuam a poder matricular e renovar a qualquer altura.
    matriculas_abertas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    rematriculas_abertas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    # Nota máxima da escala de notas da escola (ex.: 10 em Portugal/
    # Brasil, 20 em Angola/MININED) — usada por
    # cruds/diario.py::lancar_notas_lote/lancar_notas_avaliacao_lote para
    # validar o intervalo aceite ao lançar uma nota. Obrigatório (por
    # isso NOT NULL, ao contrário de nota_minima_aprovacao, que é só
    # informativo) — sem isto o motor de notas assumiria sempre 0-10,
    # o que rejeitava silenciosamente notas reais de escolas na escala
    # 0-20 (caso real: importação de mini-pautas MININED, que têm
    # notas MACT/PT até 20). server_default preserva o comportamento
    # anterior (0-10, fixo) para as escolas já existentes.
    nota_maxima: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, server_default=text("10"))

    # Ano Letivo corrente da escola — regra geral, começa num ano e
    # termina no seguinte (ex.: início em setembro de 2026, fim em
    # junho de 2027). `ano_letivo_atual` é a junção "YYYY/YYYY" dos dois
    # anos (ex.: "2026/2027") — pedido explícito do utilizador, POR
    # ISSO É STRING, ao contrário de Turma.ano_letivo/Matricula.ano_letivo,
    # que continuam um inteiro solto com só o ano de início (convenção
    # diferente, de propósito: aquelas são o ano letivo de uma
    # turma/matrícula em concreto, não o rótulo do ano letivo corrente
    # da escola). O frontend preenche-o automaticamente a partir de
    # `data_inicio_ano_letivo`/`data_fim_ano_letivo` mas continua
    # editável (ver app/schemas/configuracoes.py para a validação de
    # que o fim é posterior ao início). Nullable como todo o resto de
    # Configurações — a exceção é que o frontend força o Gestor a
    # preencher isto antes de mais nada (ver
    # core/guards/configuracao-inicial.guard.ts do lado do frontend); a
    # BD em si continua flexível.
    data_inicio_ano_letivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_ano_letivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    ano_letivo_atual: Mapped[str | None] = mapped_column(String(9), nullable=True)

    # Períodos letivos (Manhã/Tarde/Pós-Laboral) — hora de início e de
    # encerramento de cada um. Só guarda a informação nesta primeira
    # versão (referência para a equipa); ainda não é usado para validar
    # conflitos em Horários (ver models_horarios.py), que continua a
    # aceitar qualquer hora informada diretamente na aula.
    periodo_manha_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_manha_fim: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_tarde_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_tarde_fim: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_pos_laboral_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    periodo_pos_laboral_fim: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Chave do logótipo no storage (app/core/storage.py) — não guarda o
    # ficheiro em si, só a referência; None = escola sem logótipo, os
    # PDFs gerados (documentos_pdf.py) mostram só o nome em texto.
    logotipo_chave: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Página pública de apresentação da própria escola (marketing/
    # angariação de alunos, distinta da apresentação da PLATAFORMA em
    # si — ver app/api/v1/publico.py::obter_site_publico) — desativada
    # por omissão: uma escola nova não fica com uma página pública a
    # meio de preencher exposta sem querer. Texto livre, sem
    # formatação — o frontend só quebra por parágrafos.
    site_publico_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    site_publico_missao: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_publico_metodologia: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Endereço legível da página pública (ex.: "colegio-do-futuro"), em
    # vez de a escola só poder partilhar /escola/<uuid>. Único na
    # plataforma inteira (não só no tenant) porque entra num path
    # global, sem prefixo de tenant — ver cruds/site_publico.py para a
    # validação de formato e verificação de disponibilidade. NULL =
    # escola ainda não escolheu um; a página pública continua acessível
    # pelo uuid enquanto isso.
    site_publico_slug: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    # Modelo visual da página pública — um dos TEMPLATES_VALIDOS em
    # cruds/site_publico.py. String livre (não um Enum do Postgres) de
    # propósito: acrescentar um 5º modelo no futuro fica só no código
    # Python, sem migração de schema.
    site_publico_template: Mapped[str] = mapped_column(String(30), nullable=False, default="classico", server_default="classico")
    # Redes sociais — links opcionais mostrados na página pública. O
    # WhatsApp guarda só o número (ex.: "351912345678", sem "+" nem
    # espaços) porque é a partir dele que se constrói o link
    # "https://wa.me/<numero>", não é uma URL em si.
    site_publico_facebook: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site_publico_instagram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site_publico_whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)

    @property
    def tem_logotipo(self) -> bool:
        """Não é uma coluna — só facilita expor "há logótipo?" via
        ConfiguracaoTenantOut sem vazar a chave interna do storage."""
        return self.logotipo_chave is not None

    # Relacionamento
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil_acesso: Mapped[str] = mapped_column(String(50), nullable=False) # GESTOR, PROFESSOR, ALUNO
    # Suspensão individual (distinta da suspensão da escola inteira em
    # Tenant.status) — Gestor/Super Admin usam isto para revogar o
    # acesso de UMA pessoa (ex.: funcionário que saiu) sem mexer no
    # resto da escola. Só é verificado no login (ver
    # cruds/auth.py::autenticar), não em cada pedido — mesma limitação
    # já aceite para Tenant.status: uma sessão já iniciada só perde o
    # acesso quando o token expirar (até 24h), não instantaneamente.
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    # Distinto de `ativo` acima (suspensão administrativa) — este marca
    # se a conta já passou pelo link de ativação enviado por e-mail
    # (ver cruds/auth.py::registar_escola/ativar_conta e
    # models_usuarios.py::ContaAtivacaoToken). Default True de propósito:
    # só o registo self-service de uma escola nova (POST /auth/registo)
    # exige ativação — contas criadas por um Gestor já autenticado
    # (Secretaria, Professor, acessos de Aluno/Responsável) continuam a
    # poder entrar de imediato, como sempre puderam.
    email_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relacionamento
    tenant: Mapped["Tenant"] = relationship(back_populates="usuarios")