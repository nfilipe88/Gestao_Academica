import { createAction, props } from '@ngrx/store';
import { Notificacao } from './notificacoes.models';

export const carregarNotificacoes = createAction('[Notificacoes] Carregar Notificacoes');
export const carregarNotificacoesSucesso = createAction(
  '[Notificacoes] Carregar Notificacoes Sucesso',
  props<{ notificacoes: Notificacao[] }>()
);

export const carregarContagem = createAction('[Notificacoes] Carregar Contagem');
export const carregarContagemSucesso = createAction(
  '[Notificacoes] Carregar Contagem Sucesso',
  props<{ totalNaoLidas: number }>()
);

export const marcarComoLida = createAction('[Notificacoes] Marcar Como Lida', props<{ id: string }>());
export const marcarComoLidaSucesso = createAction('[Notificacoes] Marcar Como Lida Sucesso', props<{ id: string }>());

export const marcarTodasComoLidas = createAction('[Notificacoes] Marcar Todas Como Lidas');
export const marcarTodasComoLidasSucesso = createAction('[Notificacoes] Marcar Todas Como Lidas Sucesso');

// Ação genérica de falha (mesmo padrão dos restantes módulos).
export const notificacoesOperacaoFalhou = createAction(
  '[Notificacoes API] Operação Falhou',
  props<{ erro: string }>()
);
