import { createFeatureSelector, createSelector } from '@ngrx/store';
import { EventosState } from './eventos.reducer';

export const selectEventosState = createFeatureSelector<EventosState>('eventos');

export const selectEventos = createSelector(selectEventosState, (state) => state.eventos);
export const selectEventosMensagem = createSelector(selectEventosState, (state) => state.mensagem);
export const selectEventosError = createSelector(selectEventosState, (state) => state.erro);
