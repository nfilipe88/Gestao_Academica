import { createReducer, on } from '@ngrx/store';
import * as NotificacoesActions from './notificacoes.actions';
import { Notificacao } from './notificacoes.models';

export interface NotificacoesState {
  notificacoes: Notificacao[];
  totalNaoLidas: number;
  erro: string | null;
}

export const initialState: NotificacoesState = {
  notificacoes: [],
  totalNaoLidas: 0,
  erro: null
};

export const notificacoesReducer = createReducer(
  initialState,
  on(NotificacoesActions.carregarNotificacoes, (state) => ({ ...state, erro: null })),
  on(NotificacoesActions.carregarNotificacoesSucesso, (state, { notificacoes }) => ({ ...state, notificacoes })),

  on(NotificacoesActions.carregarContagemSucesso, (state, { totalNaoLidas }) => ({ ...state, totalNaoLidas })),

  // Otimista: a UI reflete de imediato, o pedido HTTP corre em paralelo.
  on(NotificacoesActions.marcarComoLidaSucesso, (state, { id }) => ({
    ...state,
    notificacoes: state.notificacoes.map((n) => (n.id === id ? { ...n, lida: true } : n)),
    totalNaoLidas: Math.max(0, state.totalNaoLidas - 1)
  })),

  on(NotificacoesActions.marcarTodasComoLidasSucesso, (state) => ({
    ...state,
    notificacoes: state.notificacoes.map((n) => ({ ...n, lida: true })),
    totalNaoLidas: 0
  })),

  on(NotificacoesActions.notificacoesOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
