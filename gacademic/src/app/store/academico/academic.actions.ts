import { createAction, props } from '@ngrx/store';
import { Curso, Turma } from './academic.models';

// Ações para Cursos
export const carregarCursos = createAction('[Academico] Carregar Cursos');
export const carregarCursosSucesso = createAction(
  '[Academico] Carregar Cursos Sucesso',
  props<{ cursos: Curso[] }>()
);
export const criarCurso = createAction(
  '[Academico] Criar Curso',
  props<{ nome: string }>()
);

// Ações para Turmas (Simplificado para o exemplo)
export const carregarTurmas = createAction('[Academico] Carregar Turmas');
export const carregarTurmasSucesso = createAction(
  '[Academico] Carregar Turmas Sucesso',
  props<{ turmas: Turma[] }>()
);
export const criarTurma = createAction(
  '[Academico] Criar Turma',
  props<{ curso_id: string, nome_codigo: string, ano_letivo: number, vagas_maximas: number }>()
);

// Ação genérica de falha: cobre qualquer um dos pedidos acima (carregar ou
// criar cursos/turmas). Sem isto, um erro HTTP dentro de um effect fica por
// apanhar e mata esse effect para o resto da sessão (ver academic.effects.ts).
export const academicoOperacaoFalhou = createAction(
  '[Academico API] Operação Falhou',
  props<{ erro: string }>()
);
