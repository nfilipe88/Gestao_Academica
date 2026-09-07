import { createReducer, on } from '@ngrx/store';
import * as EventosActions from './eventos.actions';
import { Evento } from './eventos.models';

export interface EventosState {
  eventos: Evento[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: EventosState = {
  eventos: [],
  mensagem: null,
  erro: null
};

export const eventosReducer = createReducer(
  initialState,
  on(EventosActions.carregarEventos, EventosActions.criarEvento, EventosActions.atualizarEvento,
     EventosActions.removerEvento, EventosActions.adicionarFotoEvento, EventosActions.removerFotoEvento,
    (state) => ({ ...state, erro: null })
  ),
  on(EventosActions.carregarEventosSucesso, (state, { eventos }) => ({ ...state, eventos })),
  on(EventosActions.eventosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(EventosActions.eventosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
