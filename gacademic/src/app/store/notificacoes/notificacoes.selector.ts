import { createFeatureSelector, createSelector } from '@ngrx/store';
import { NotificacoesState } from './notificacoes.reducer';

export const selectNotificacoesState = createFeatureSelector<NotificacoesState>('notificacoes');

export const selectNotificacoes = createSelector(selectNotificacoesState, (state) => state.notificacoes);
export const selectTotalNaoLidas = createSelector(selectNotificacoesState, (state) => state.totalNaoLidas);
export const selectNotificacoesError = createSelector(selectNotificacoesState, (state) => state.erro);
