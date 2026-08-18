import { createFeatureSelector, createSelector } from '@ngrx/store';
import { PermissoesState } from './permissoes.reducer';

export const selectPermissoesState = createFeatureSelector<PermissoesState>('permissoes');

export const selectPermissoes = createSelector(selectPermissoesState, (state) => state.permissoes);
export const selectPermissoesError = createSelector(selectPermissoesState, (state) => state.erro);
