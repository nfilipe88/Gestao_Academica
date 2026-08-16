import { createFeatureSelector, createSelector } from '@ngrx/store';
import { ConfiguracoesState } from './configuracoes.reducer';

export const selectConfiguracoesState = createFeatureSelector<ConfiguracoesState>('configuracoes');

export const selectConfiguracao = createSelector(selectConfiguracoesState, (state) => state.configuracao);
// Moeda pronta a usar em `| currency:(moeda$ | async)` — nunca undefined,
// mesmo antes da configuração carregar (evita o pipe currency partir a
// app inteira num primeiro render antes do carregarConfiguracao() responder).
export const selectMoeda = createSelector(selectConfiguracao, (config) => config.moeda || 'EUR');
export const selectConfiguracoesMensagem = createSelector(selectConfiguracoesState, (state) => state.mensagem);
export const selectConfiguracoesError = createSelector(selectConfiguracoesState, (state) => state.erro);
export const selectTiposAvaliacao = createSelector(selectConfiguracoesState, (state) => state.tiposAvaliacao);
// Só os ativos, para popular o <select> de tipo ao criar uma Avaliação no Diário.
export const selectTiposAvaliacaoAtivos = createSelector(selectTiposAvaliacao, (tipos) => tipos.filter(t => t.ativo));
