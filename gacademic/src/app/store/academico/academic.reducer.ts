import { createReducer, on } from '@ngrx/store';
import * as AcademicoActions from './academic.actions';
import { Curso, Turma } from './academic.models';

export interface AcademicoState {
  cursos: Curso[];
  turmas: Turma[];
  erro: string | null;
}

export const initialState: AcademicoState = {
  cursos: [],
  turmas: [],
  erro: null
};

export const academicoReducer = createReducer(
  initialState,
  on(AcademicoActions.carregarCursos, AcademicoActions.criarCurso,
     AcademicoActions.carregarTurmas, AcademicoActions.criarTurma,
    (state) => ({ ...state, erro: null })
  ),
  on(AcademicoActions.carregarCursosSucesso, (state, { cursos }) => ({ ...state, cursos })),
  on(AcademicoActions.carregarTurmasSucesso, (state, { turmas }) => ({ ...state, turmas })),
  on(AcademicoActions.academicoOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
