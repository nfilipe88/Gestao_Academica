import { createReducer, on } from '@ngrx/store';
import * as TransferenciasActions from './transferencias.actions';
import { SolicitacaoTransferencia } from './transferencias.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface TransferenciasState {
  solicitacoes: SolicitacaoTransferencia[];
  paginacao: EstadoPaginacao;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: TransferenciasState = {
  solicitacoes: [],
  paginacao: PAGINACAO_INICIAL,
  mensagem: null,
  erro: null,
};

export const transferenciasReducer = createReducer(
  initialState,
  on(TransferenciasActions.carregarSolicitacoesSucesso, (state, { solicitacoes, paginacao }) => ({ ...state, solicitacoes, paginacao, erro: null })),
  on(TransferenciasActions.transferenciasOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(TransferenciasActions.transferenciasOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
