// Alinhado com a forma devolvida por GET /api/v1/turmas/{turma_id}/matriculas
// (app/api/v1/matriculas.py) — já vem com o nome do aluno resolvido pelo
// back-end (join com Aluno). turma_id não vem no payload do back-end (é
// implícito no URL do pedido); é injetado aqui no cliente para conseguirmos
// filtrar por turma no reducer.
export interface MatriculaDaTurma {
  matricula_id: string;
  turma_id: string;
  aluno_id: string;
  nome_aluno: string;
  matricula_interna: string;
  status_matricula: string; // ATIVO, TRANSFERIDO, TRANCADO, EVADIDO
  ano_letivo: number;
  data_matricula: string;
}

export const ESTADOS_MATRICULA = ['ATIVO', 'TRANSFERIDO', 'TRANCADO', 'EVADIDO'] as const;
