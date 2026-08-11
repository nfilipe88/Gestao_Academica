// Alinhado com app/api/v1/professores.py.
export interface Professor {
  id: string;
  usuario_id: string;
  nome_completo: string;
  email: string;
  formacao_academica: string | null;
  data_criacao: string;
}

export interface Alocacao {
  id: string;
  professor_id: string;
  turma_id: string;
  nome_turma: string;
  disciplina_id: string;
  nome_disciplina: string;
}
