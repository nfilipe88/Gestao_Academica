import { createReducer, on } from '@ngrx/store';
import * as TransferenciasActions from './transferencias.actions';
import { SolicitacaoTransferencia } from './transferencias.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

interface ListaSolicitacoes {
  solicitacoes: SolicitacaoTransferencia[];
  paginacao: EstadoPaginacao;
}

export interface TransferenciasState {
  // Três listas independentes — ver comentário em transferencias.actions.ts.
  enviadas: ListaSolicitacoes;
  recebidas: ListaSolicitacoes;
  auditoria: ListaSolicitacoes;
  mensagem: string | null;
  erro: string | null;
}

const listaVazia: ListaSolicitacoes = { solicitacoes: [], paginacao: PAGINACAO_INICIAL };

export const initialState: TransferenciasState = {
  enviadas: listaVazia,
  recebidas: listaVazia,
  auditoria: listaVazia,
  mensagem: null,
  erro: null,
};

export const transferenciasReducer = createReducer(
  initialState,
  on(TransferenciasActions.carregarEnviadasSucesso, (state, { solicitacoes, paginacao }) => ({
    ...state, enviadas: { solicitacoes, paginacao }, erro: null
  })),
  on(TransferenciasActions.carregarRecebidasSucesso, (state, { solicitacoes, paginacao }) => ({
    ...state, recebidas: { solicitacoes, paginacao }, erro: null
  })),
  on(TransferenciasActions.carregarAuditoriaSucesso, (state, { solicitacoes, paginacao }) => ({
    ...state, auditoria: { solicitacoes, paginacao }, erro: null
  })),
  on(TransferenciasActions.transferenciasOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(TransferenciasActions.transferenciasOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
