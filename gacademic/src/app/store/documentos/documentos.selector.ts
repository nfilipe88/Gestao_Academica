import { createFeatureSelector, createSelector } from '@ngrx/store';
import { DocumentosState } from './documentos.reducer';

export const selectDocumentosState = createFeatureSelector<DocumentosState>('documentos');

export const selectPrecosDocumento = createSelector(selectDocumentosState, (state) => state.precos);
export const selectSolicitacoesEmissao = createSelector(selectDocumentosState, (state) => state.solicitacoesEmissao);
export const selectUltimaCobrancaDocumento = createSelector(selectDocumentosState, (state) => state.ultimaCobranca);
export const selectSolicitacoesEscolaStaff = createSelector(selectDocumentosState, (state) => state.solicitacoesEscolaStaff);
export const selectMinhasSolicitacoesEscola = createSelector(selectDocumentosState, (state) => state.minhasSolicitacoesEscola);
export const selectDocumentosMensagem = createSelector(selectDocumentosState, (state) => state.mensagem);
export const selectDocumentosError = createSelector(selectDocumentosState, (state) => state.erro);
