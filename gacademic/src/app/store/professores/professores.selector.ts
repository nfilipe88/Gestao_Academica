import { createFeatureSelector, createSelector } from '@ngrx/store';
import { ProfessoresState } from './professores.reducer';

export const selectProfessoresState = createFeatureSelector<ProfessoresState>('professores');

export const selectProfessores = createSelector(
  selectProfessoresState,
  (state) => state.professores
);

export const selectAlocacoes = createSelector(
  selectProfessoresState,
  (state) => state.alocacoes
);

export const selectProfessoresError = createSelector(
  selectProfessoresState,
  (state) => state.erro
);
