import { createFeatureSelector, createSelector } from '@ngrx/store';
import { IndicadoresState } from './indicadores.reducer';

export const selectIndicadoresState = createFeatureSelector<IndicadoresState>('indicadores');

export const selectIndicadores = createSelector(selectIndicadoresState, (state) => state.indicadores);
export const selectAlunosEmRisco = createSelector(selectIndicadoresState, (state) => state.alunosEmRisco);
export const selectTrilhasPorMatricula = createSelector(selectIndicadoresState, (state) => state.trilhasPorMatricula);
export const selectAGerarTrilhaPorMatricula = createSelector(selectIndicadoresState, (state) => state.aGerarTrilhaPorMatricula);
export const selectIndicadoresError = createSelector(selectIndicadoresState, (state) => state.erro);
