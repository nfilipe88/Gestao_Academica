import { createFeatureSelector, createSelector } from '@ngrx/store';
import { SuporteState } from './suporte.reducer';

export const selectSuporteState = createFeatureSelector<SuporteState>('suporte');

export const selectMeusTickets = createSelector(selectSuporteState, (state) => state.tickets);
export const selectPaginacaoTickets = createSelector(selectSuporteState, (state) => state.paginacao);
export const selectTicketAtual = createSelector(selectSuporteState, (state) => state.ticketAtual);
export const selectSuporteMensagem = createSelector(selectSuporteState, (state) => state.mensagem);
export const selectSuporteErro = createSelector(selectSuporteState, (state) => state.erro);
