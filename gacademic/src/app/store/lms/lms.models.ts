// Alinhado com app/api/v1/lms.py — LMS mínimo (materiais de aula).

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
