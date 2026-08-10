import { createFeatureSelector, createSelector } from '@ngrx/store';
import { MatriculasState } from './matriculas.reducer';

export const selectMatriculasState = createFeatureSelector<MatriculasState>('matriculas');

export const selectMatriculasPorTurma = createSelector(
  selectMatriculasState,
  (state) => state.porTurma
);

export const selectMatriculasError = createSelector(
  selectMatriculasState,
  (state) => state.erro
);
