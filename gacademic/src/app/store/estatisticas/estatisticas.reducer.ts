import { createReducer, on } from '@ngrx/store';
import * as EstatisticasActions from './estatisticas.actions';
import { DashboardEstatisticas, RelatorioEstatisticas } from './estatisticas.models';

export interface EstatisticasState {
  dashboard: DashboardEstatisticas | null;
  relatorio: RelatorioEstatisticas | null;
  erro: string | null;
}

export const initialState: EstatisticasState = {
  dashboard: null,
  relatorio: null,
  erro: null,
};

export const estatisticasReducer = createReducer(
  initialState,
  on(EstatisticasActions.carregarDashboardEstatisticas, EstatisticasActions.carregarRelatorioEstatisticas, (state) => ({ ...state, erro: null })),
  on(EstatisticasActions.carregarDashboardEstatisticasSucesso, (state, { dashboard }) => ({ ...state, dashboard })),
  on(EstatisticasActions.carregarRelatorioEstatisticasSucesso, (state, { relatorio }) => ({ ...state, relatorio })),
  on(EstatisticasActions.estatisticasOperacaoFalhou, (state, { erro }) => ({ ...state, erro })),
);
