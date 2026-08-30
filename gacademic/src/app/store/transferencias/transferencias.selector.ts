import { createFeatureSelector, createSelector } from '@ngrx/store';
import { TransferenciasState } from './transferencias.reducer';

export const selectTransferenciasState = createFeatureSelector<TransferenciasState>('transferencias');

export const selectSolicitacoesEnviadas = createSelector(selectTransferenciasState, (state) => state.enviadas.solicitacoes);
export const selectPaginacaoEnviadas = createSelector(selectTransferenciasState, (state) => state.enviadas.paginacao);

export const selectSolicitacoesRecebidas = createSelector(selectTransferenciasState, (state) => state.recebidas.solicitacoes);
export const selectPaginacaoRecebidas = createSelector(selectTransferenciasState, (state) => state.recebidas.paginacao);

export const selectSolicitacoesAuditoria = createSelector(selectTransferenciasState, (state) => state.auditoria.solicitacoes);
export const selectPaginacaoAuditoria = createSelector(selectTransferenciasState, (state) => state.auditoria.paginacao);

export const selectTransferenciasMensagem = createSelector(selectTransferenciasState, (state) => state.mensagem);
export const selectTransferenciasError = createSelector(selectTransferenciasState, (state) => state.erro);
