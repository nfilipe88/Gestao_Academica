import { createReducer, on } from '@ngrx/store';
import * as AcademicoActions from './academic.actions';

export interface AcademicoState {
  cursos: any[];
  turmas: any[];
}

export const initialState: AcademicoState = {
  cursos: [],
  turmas: []
};

export const academicoReducer = createReducer(
  initialState,
  on(AcademicoActions.carregarCursosSucesso, (state, { cursos }) => ({ ...state, cursos })),
  on(AcademicoActions.carregarTurmasSucesso, (state, { turmas }) => ({ ...state, turmas }))
);
