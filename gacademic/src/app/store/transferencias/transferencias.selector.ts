import { createFeatureSelector, createSelector } from '@ngrx/store';
import { TransferenciasState } from './transferencias.reducer';

export const selectTransferenciasState = createFeatureSelector<TransferenciasState>('transferencias');

export const selectSolicitacoesTransferencia = createSelector(selectTransferenciasState, (state) => state.solicitacoes);
export const selectPaginacaoTransferencias = createSelector(selectTransferenciasState, (state) => state.paginacao);
export const selectTransferenciasMensagem = createSelector(selectTransferenciasState, (state) => state.mensagem);
export const selectTransferenciasError = createSelector(selectTransferenciasState, (state) => state.erro);
