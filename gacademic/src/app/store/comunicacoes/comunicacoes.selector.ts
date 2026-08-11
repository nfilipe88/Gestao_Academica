import { createFeatureSelector, createSelector } from '@ngrx/store';
import { ComunicacoesState } from './comunicacoes.reducer';

export const selectComunicacoesState = createFeatureSelector<ComunicacoesState>('comunicacoes');

export const selectComunicados = createSelector(
  selectComunicacoesState,
  (state) => state.comunicados
);

export const selectComunicacoesError = createSelector(
  selectComunicacoesState,
  (state) => state.erro
);
