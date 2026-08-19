import { createFeatureSelector, createSelector } from '@ngrx/store';
import { PropinasState } from './propinas.reducer';

export const selectPropinasState = createFeatureSelector<PropinasState>('propinas');

export const selectLinhasPropinas = createSelector(selectPropinasState, (state) => state.linhas);
export const selectPropinasError = createSelector(selectPropinasState, (state) => state.erro);
