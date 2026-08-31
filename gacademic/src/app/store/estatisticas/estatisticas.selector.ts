import { createFeatureSelector, createSelector } from '@ngrx/store';
import { EstatisticasState } from './estatisticas.reducer';

export const selectEstatisticasState = createFeatureSelector<EstatisticasState>('estatisticas');

export const selectDashboardEstatisticas = createSelector(selectEstatisticasState, (state) => state.dashboard);
export const selectRelatorioEstatisticas = createSelector(selectEstatisticasState, (state) => state.relatorio);
export const selectEstatisticasError = createSelector(selectEstatisticasState, (state) => state.erro);
