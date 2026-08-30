import { createAction, props } from '@ngrx/store';
import { MatriculaDaTurma } from './matriculas.models';

export const carregarMatriculasDaTurma = createAction(
  '[Matriculas] Carregar Matriculas Da Turma',
  props<{ turma_id: string }>()
);
export const carregarMatriculasDaTurmaSucesso = createAction(
  '[Matriculas] Carregar Matriculas Da Turma Sucesso',
  props<{ turma_id: string, matriculas: MatriculaDaTurma[] }>()
);

export const criarMatricula = createAction(
  '[Matriculas] Criar Matricula',
  props<{ aluno_id: string, turma_id: string, ano_letivo: number }>()
);

export const atualizarStatusMatricula = createAction(
  '[Matriculas] Atualizar Status Matricula',
  props<{ matricula_id: string, turma_id: string, status_matricula: string, motivo?: string | null }>()
);

// Ação genérica de falha (mesmo padrão dos módulos académico/alunos): sem
// isto, um erro HTTP dentro de um effect fica por apanhar e mata esse
// effect para o resto da sessão.
export const matriculasOperacaoFalhou = createAction(
  '[Matriculas API] Operação Falhou',
  props<{ erro: string }>()
);
