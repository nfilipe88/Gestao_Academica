// Alinhado com app/api/v1/tarefas.py.

export interface Tarefa {
  id: string;
  alocacao_id: string;
  titulo: string;
  descricao: string | null;
  data_entrega: string; // ISO (YYYY-MM-DD)
  valor_maximo: number;
  periodo_avaliacao: string | null;
  data_criacao: string;
  turma_id: string;
  nome_turma: string;
  disciplina_id: string;
  nome_disciplina: string;
  pendentes: number; // nº de entregas ainda por corrigir (TarefaAvaliacao "PENDENTE")
}

// PENDENTE = ainda por avaliar; as restantes são escolhidas pelo professor ao avaliar.
export type StatusEntrega = 'PENDENTE' | 'ENTREGUE' | 'ENTREGUE_ATRASADO' | 'NAO_ENTREGUE';

export interface AvaliacaoAluno {
  id: string;
  matricula_id: string;
  nome_aluno: string;
  matricula_interna: string;
  status: StatusEntrega;
  nota: number | null;
  observacoes: string | null;
  data_avaliacao: string | null;
}

export interface TarefaComAvaliacoes extends Tarefa {
  avaliacoes: AvaliacaoAluno[];
}

export interface AvaliacaoAlunoInput {
  matricula_id: string;
  status: StatusEntrega;
  nota: number | null;
  observacoes: string | null;
}
