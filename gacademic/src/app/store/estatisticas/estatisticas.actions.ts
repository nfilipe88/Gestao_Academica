import { createAction, props } from '@ngrx/store';
import { DashboardEstatisticas, RelatorioEstatisticas } from './estatisticas.models';

// tenant_id é opcional em todas as ações: omitido = a própria escola de
// quem está autenticado (Gestor/Secretaria, usa /api/v1/estatisticas);
// presente = qualquer escola, usado pelo Super Admin depois de a
// escolher (usa /api/v1/admin/tenants/{tenant_id}/estatisticas) — ver
// estatisticas.effects.ts::baseUrl. Mesma store, dois consumidores
// (mesmo padrão de store/usuarios).

export const carregarDashboardEstatisticas = createAction(
  '[Estatísticas] Carregar Dashboard',
  props<{ tenant_id?: string }>()
);
export const carregarDashboardEstatisticasSucesso = createAction(
  '[Estatísticas] Carregar Dashboard Sucesso',
  props<{ dashboard: DashboardEstatisticas }>()
);

export const carregarRelatorioEstatisticas = createAction(
  '[Estatísticas] Carregar Relatório',
  props<{ data_inicio: string, data_fim: string, tenant_id?: string }>()
);
export const carregarRelatorioEstatisticasSucesso = createAction(
  '[Estatísticas] Carregar Relatório Sucesso',
  props<{ relatorio: RelatorioEstatisticas }>()
);

export const estatisticasOperacaoFalhou = createAction(
  '[Estatísticas API] Operação Falhou',
  props<{ erro: string }>()
);
