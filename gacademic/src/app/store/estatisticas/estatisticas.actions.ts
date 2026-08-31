import { createAction, props } from '@ngrx/store';
import { DashboardEstatisticas, RelatorioEstatisticas } from './estatisticas.models';

export const carregarDashboardEstatisticas = createAction('[Estatísticas] Carregar Dashboard');
export const carregarDashboardEstatisticasSucesso = createAction(
  '[Estatísticas] Carregar Dashboard Sucesso',
  props<{ dashboard: DashboardEstatisticas }>()
);

export const carregarRelatorioEstatisticas = createAction(
  '[Estatísticas] Carregar Relatório',
  props<{ data_inicio: string, data_fim: string }>()
);
export const carregarRelatorioEstatisticasSucesso = createAction(
  '[Estatísticas] Carregar Relatório Sucesso',
  props<{ relatorio: RelatorioEstatisticas }>()
);

export const estatisticasOperacaoFalhou = createAction(
  '[Estatísticas API] Operação Falhou',
  props<{ erro: string }>()
);
