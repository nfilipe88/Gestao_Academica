import { createAction, props } from '@ngrx/store';
import { Indicadores } from './indicadores.models';

export const carregarIndicadores = createAction('[Indicadores] Carregar Indicadores');
export const carregarIndicadoresSucesso = createAction(
  '[Indicadores] Carregar Indicadores Sucesso',
  props<{ indicadores: Indicadores }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const indicadoresOperacaoFalhou = createAction(
  '[Indicadores API] Operação Falhou',
  props<{ erro: string }>()
);
