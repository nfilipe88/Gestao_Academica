import { createReducer, on } from '@ngrx/store';
import * as SuporteActions from './suporte.actions';
import { TicketComMensagens, TicketRegisto } from './suporte.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface SuporteState {
  tickets: TicketRegisto[];
  paginacao: EstadoPaginacao;
  ticketAtual: TicketComMensagens | null;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: SuporteState = {
  tickets: [],
  paginacao: PAGINACAO_INICIAL,
  ticketAtual: null,
  mensagem: null,
  erro: null,
};

export const suporteReducer = createReducer(
  initialState,
  on(SuporteActions.carregarMeusTickets, SuporteActions.criarTicket, SuporteActions.carregarTicket, SuporteActions.enviarMensagemTicket,
    (state) => ({ ...state, erro: null })
  ),
  on(SuporteActions.carregarMeusTicketsSucesso, (state, { tickets, paginacao }) => ({ ...state, tickets, paginacao })),
  on(SuporteActions.carregarTicketSucesso, (state, { ticket }) => ({ ...state, ticketAtual: ticket })),
  on(SuporteActions.suporteOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(SuporteActions.suporteOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
