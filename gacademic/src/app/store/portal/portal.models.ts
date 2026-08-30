// Alinhado com app/api/v1/portal.py.
import { FaturaMensalidade } from '../financeiro/financeiro.models';

export interface EducandoResumo {
  aluno_id: string;
  nome_completo: string;
  matricula_interna: string;
  matricula_id: string | null;
  status_matricula: string | null;
  ano_letivo: number | null;
  nome_turma: string | null;
  // Resumo — um responsável pode ter vários educandos; isto permite
  // assinalar quem precisa de atenção sem abrir o financeiro de cada
  // um (ver app/cruds/portal.py::_tem_propina_em_atraso).
  tem_propina_em_atraso: boolean;
  // Rematrícula self-service (ver app/cruds/portal.py::pedir_rematricula)
  // — elegivel_rematricula é false quando a matrícula não está ATIVO ou
  // já existe matrícula para o ano seguinte (nada a pedir).
  elegivel_rematricula: boolean;
  bloqueado_rematricula_por_atraso: boolean;
  pedido_rematricula_confirmado: boolean;
  ano_letivo_destino_rematricula: number | null;
}

// A grade horária reaproveita exatamente o formato de HorarioAula do
// módulo Horários (ver store/horarios/horarios.models.ts) — o Portal só
// lê, nunca cria/edita, por isso não precisa de repetir o tipo aqui.
export interface HorarioAulaPortal {
  id: string;
  dia_semana: number;
  hora_inicio: string;
  hora_fim: string;
  sala: string | null;
  nome_turma: string;
  nome_disciplina: string;
  nome_professor: string;
}

export interface NotaBoletim {
  periodo_avaliacao: string;
  tipo_avaliacao: string | null;
  data_avaliacao: string | null;
  valor_nota: number;
}

export interface DisciplinaBoletim {
  disciplina_id: string;
  nome_disciplina: string;
  notas: NotaBoletim[];
  total_aulas: number;
  total_faltas: number;
}

export interface Boletim {
  disciplinas: DisciplinaBoletim[];
}

// Formato reduzido — o extrato de faturas em si reaproveita
// FaturaMensalidade de store/financeiro/financeiro.models.ts.
export interface FinanceiroEducando {
  matricula_id: string | null;
  contrato: {
    id: string;
    valor_total_anual: number;
    quantidade_parcelas: number;
  } | null;
  faturas: FaturaMensalidade[];
}

// Alinhado com cruds/tarefas.py::listar_tarefas_do_aluno.
export interface TarefaEducando {
  tarefa_id: string;
  titulo: string;
  descricao: string | null;
  data_entrega: string;
  valor_maximo: number;
  nome_turma: string;
  nome_disciplina: string;
  status: 'PENDENTE' | 'ENTREGUE' | 'ENTREGUE_ATRASADO' | 'NAO_ENTREGUE';
  nota: number | null;
  observacoes: string | null;
}

// LMS mínimo — materiais de aula (ver cruds/portal.py::listar_materiais_do_educando).
export interface MaterialEducando {
  id: string;
  titulo: string;
  disciplina_id: string;
  nome_disciplina: string;
  data_criacao: string;
}

export interface MaterialEducandoDetalhe {
  id: string;
  titulo: string;
  corpo: string;
  disciplina_id: string;
  nome_objetivo: string | null;
}

// Prof. Virtual — chat sem persistência (o histórico viaja em cada
// pedido, ver store/portal/portal.effects.ts).
export interface MensagemProfVirtual {
  papel: 'aluno' | 'assistente';
  texto: string;
}

// ==========================================
// Exames online (LMS) — ver cruds/portal.py (secção G).
// ==========================================
export interface ExameEducando {
  id: string;
  titulo: string;
  nome_disciplina: string;
  data_inicio: string;
  data_fim: string;
  duracao_minutos: number;
  status_tentativa: 'NAO_INICIADA' | 'EM_CURSO' | 'SUBMETIDA';
  pode_iniciar: boolean;
  nota_obtida: number | null;
  nota_maxima: number | null;
}

export interface PerguntaTentativa {
  id: string;
  enunciado: string;
  tipo: 'ESCOLHA_MULTIPLA' | 'VERDADEIRO_FALSO';
  opcoes: string[];
}

// Nunca inclui resposta_correta — o back-end só a devolve depois de
// submetida (ver ResultadoExame).
export interface TentativaIniciada {
  tentativa_id: string;
  titulo: string;
  data_inicio_tentativa: string;
  duracao_minutos: number;
  perguntas: PerguntaTentativa[];
  respostas_ja_dadas: Record<string, string>;
}

export interface PerguntaResultado {
  id: string;
  enunciado: string;
  tipo: string;
  opcoes: string[];
  resposta_correta: string;
  resposta_dada: string | null;
  correta: boolean;
}

export interface ResultadoExame {
  nota_obtida: number;
  nota_maxima: number;
  data_submissao: string;
  perguntas: PerguntaResultado[];
}

// ==========================================
// Dashboard (Estatísticas) — ver cruds/portal.py::obter_estatisticas_do_educando.
// ==========================================
export interface DisciplinaEstatistica {
  disciplina_id: string;
  nome_disciplina: string;
  media: number;
  quantidade_notas: number;
}

// Ver app/cruds/comportamento.py — registos de comportamento
// (positivo/negativo) da matrícula atual do educando.
export interface RegistoComportamento {
  id: string;
  tipo: 'POSITIVO' | 'NEGATIVO';
  descricao: string;
  data_ocorrencia: string;
  disciplina_id: string | null;
  registrado_por_nome: string;
  data_criacao: string;
}

export interface ResumoComportamento {
  total_positivos: number;
  total_negativos: number;
  recentes: RegistoComportamento[];
}

export interface EstatisticasEducando {
  media_geral: number | null;
  media_por_disciplina: DisciplinaEstatistica[];
  taxa_assiduidade: number | null; // percentagem, 0-100
  total_faltas: number;
  total_aulas: number;
  tendencia_notas: 'SUBIU' | 'DESCEU' | 'ESTAVEL' | null;
  comportamento: ResumoComportamento;
}

// Comunicados — histórico de consulta (o e-mail já foi enviado na hora
// do envio, ver cruds/comunicacoes.py::criar_comunicado).
export interface ComunicadoEducando {
  id: string;
  autor_nome: string;
  tipo: 'COMUNICADO' | 'CONVOCATORIA';
  titulo: string;
  corpo: string;
  destinatario_tipo: 'TURMA' | 'ALUNO' | 'ESCOLA';
  data_envio: string;
  tem_anexo: boolean;
}
