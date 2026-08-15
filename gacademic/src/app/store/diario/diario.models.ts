// Alinhado com app/api/v1/diario.py.

export interface AlunoDiario {
  matricula_id: string;
  nome_aluno: string;
  matricula_interna: string;
  numero_chamada: number;
}

export interface ConsolidadoTurmaDisciplina {
  total_alunos: number;
  media_turma: number | null;
  alunos_abaixo_da_media: number;
  total_faltas: number;
}

export interface FrequenciaAlunoInput {
  matricula_id: string;
  presenca: boolean;
  faltas: number;
}

export interface NotaAlunoInput {
  matricula_id: string;
  valor_nota: number;
}

export interface PeriodoAvaliacao {
  id: string;
  nome: string;
  aberto: boolean;
  data_fecho: string | null;
}

export const TIPOS_AVALIACAO = ['CONTINUA', 'PROVA'] as const;
export type TipoAvaliacao = typeof TIPOS_AVALIACAO[number];

// Uma prova ou avaliação contínua concreta dentro de um período — a
// nota final do período (ver NotaFinal) passa a ser a média ponderada
// (por "peso") das avaliações com nota lançada nesse período.
export interface Avaliacao {
  id: string;
  turma_id: string;
  disciplina_id: string;
  periodo_avaliacao: string;
  titulo: string;
  tipo_avaliacao: TipoAvaliacao;
  peso: number;
  data_avaliacao: string | null;
  objetivo_aprendizagem_id: string | null;
  data_criacao: string;
}

export interface NotaAvaliacaoInput {
  matricula_id: string;
  valor_nota: number;
}

// Nota final de um aluno num período — calculada a partir das
// avaliações (calculada_automaticamente=true) ou lançada diretamente
// à mão (lançamentos antigos, antes desta funcionalidade existir).
export interface NotaFinal {
  matricula_id: string;
  nome_aluno: string;
  valor_nota: number | null;
  calculada_automaticamente: boolean;
}
