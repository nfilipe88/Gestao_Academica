// Alinhado com app/api/v1/lms.py — materiais de aula + banco de questões + exames.

export interface MaterialAula {
  id: string;
  turma_id: string;
  disciplina_id: string;
  titulo: string;
  corpo: string;
  objetivo_aprendizagem_id: string | null;
  publicado: boolean;
  data_criacao: string;
}

// ==========================================
// BANCO DE QUESTÕES
// ==========================================
export type TipoQuestaoLms = 'ESCOLHA_MULTIPLA' | 'VERDADEIRO_FALSO';

export interface LmsQuestao {
  id: string;
  disciplina_id: string;
  enunciado: string;
  tipo: TipoQuestaoLms;
  opcoes: string[];
  resposta_correta: string;
  valor: number;
}

// ==========================================
// EXAMES (motor online)
// ==========================================
export interface LmsExame {
  id: string;
  alocacao_id: string;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  duracao_minutos: number;
  baralhar_perguntas: boolean;
  publicado: boolean;
}

// Detalhe com gabarito — só para o professor/staff (ver obter_exame_com_gabarito).
export interface LmsExameDetalhe {
  id: string;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  duracao_minutos: number;
  baralhar_perguntas: boolean;
  publicado: boolean;
  perguntas: LmsQuestao[];
}

export interface LmsResultadoAlunoExame {
  matricula_id: string;
  nome_aluno: string;
  status: 'EM_CURSO' | 'SUBMETIDA';
  nota_obtida: number | null;
  nota_maxima: number | null;
  eventos_suspeitos: number;
  data_inicio: string;
  data_submissao: string | null;
}
