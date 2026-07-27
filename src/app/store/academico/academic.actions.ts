import { createAction, props } from '@ngrx/store';

// Ações para Cursos
export const carregarCursos = createAction('[Academico] Carregar Cursos');
export const carregarCursosSucesso = createAction(
  '[Academico] Carregar Cursos Sucesso',
  props<{ cursos: any[] }>()
);
export const criarCurso = createAction(
  '[Academico] Criar Curso',
  props<{ nome: string }>()
);

// Ações para Turmas (Simplificado para o exemplo)
export const carregarTurmas = createAction('[Academico] Carregar Turmas');
export const carregarTurmasSucesso = createAction(
  '[Academico] Carregar Turmas Sucesso',
  props<{ turmas: any[] }>()
);
export const criarTurma = createAction(
  '[Academico] Criar Turma',
  props<{ curso_id: string, nome_codigo: string, ano_letivo: number, vagas_maximas: number }>()
);
