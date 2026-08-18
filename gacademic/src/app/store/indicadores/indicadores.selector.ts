import { createFeatureSelector, createSelector } from '@ngrx/store';
import { IndicadoresState } from './indicadores.reducer';

export const selectIndicadoresState = createFeatureSelector<IndicadoresState>('indicadores');

export const selectIndicadores = createSelector(selectIndicadoresState, (state) => state.indicadores);
export const selectAlunosEmRisco = createSelector(selectIndicadoresState, (state) => state.alunosEmRisco);
export const selectIndicadoresError = createSelector(selectIndicadoresState, (state) => state.erro);
