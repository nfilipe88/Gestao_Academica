import { createReducer, on } from '@ngrx/store';
import * as TransferenciasActions from './transferencias.actions';
import { SolicitacaoTransferencia } from './transferencias.models';

export interface TransferenciasState {
  solicitacoes: SolicitacaoTransferencia[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: TransferenciasState = {
  solicitacoes: [],
  mensagem: null,
  erro: null,
};

export const transferenciasReducer = createReducer(
  initialState,
  on(TransferenciasActions.carregarSolicitacoesSucesso, (state, { solicitacoes }) => ({ ...state, solicitacoes, erro: null })),
  on(TransferenciasActions.transferenciasOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(TransferenciasActions.transferenciasOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
