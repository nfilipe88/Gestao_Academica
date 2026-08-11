import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AcademicoState } from './academic.reducer';

export const selectAcademicoState = createFeatureSelector<AcademicoState>('academico');

export const selectCursos = createSelector(
  selectAcademicoState,
  (state) => state.cursos
);

export const selectSeries = createSelector(
  selectAcademicoState,
  (state) => state.series
);

export const selectTurmas = createSelector(
  selectAcademicoState,
  (state) => state.turmas
);

export const selectDisciplinas = createSelector(
  selectAcademicoState,
  (state) => state.disciplinas
);

export const selectGradeCurricular = createSelector(
  selectAcademicoState,
  (state) => state.gradeCurricular
);

export const selectAcademicoError = createSelector(
  selectAcademicoState,
  (state) => state.erro
);
