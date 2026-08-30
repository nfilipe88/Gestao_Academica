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
  status_matricula: string; // ATIVO, TRANSFERIDO, TRANCADO, EVADIDO, CICLO_CONCLUIDO
  ano_letivo: number;
  data_matricula: string;
}

// CICLO_CONCLUIDO ("Fim de Ciclo") tem um sub-fluxo próprio no
// template (motivo obrigatório) — ver turmas.component.ts. Fica na
// mesma lista para o <select> de sempre continuar a listar todos os
// estados possíveis.
export const ESTADOS_MATRICULA = ['ATIVO', 'TRANSFERIDO', 'TRANCADO', 'EVADIDO', 'CICLO_CONCLUIDO'] as const;

// Só usados quando status_matricula === 'CICLO_CONCLUIDO' — têm de
// ficar sincronizados com MOTIVOS_FIM_CICLO_VALIDOS em
// back_end/app/cruds/matriculas.py.
export const MOTIVOS_FIM_CICLO = [
  { chave: 'TRANSFERENCIA_EXTERNA', rotulo: 'Foi para uma escola fora da plataforma' },
  { chave: 'CONCLUSAO_ESCOLARIDADE', rotulo: 'Concluiu a escolaridade' },
  { chave: 'OUTRO', rotulo: 'Outro motivo' },
] as const;

export interface MatriculaDocumento {
  id: string;
  descricao: string | null;
  nome_original: string;
}
