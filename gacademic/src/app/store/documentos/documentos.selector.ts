import { createFeatureSelector, createSelector } from '@ngrx/store';
import { DocumentosState } from './documentos.reducer';

export const selectDocumentosState = createFeatureSelector<DocumentosState>('documentos');

export const selectPrecosDocumento = createSelector(selectDocumentosState, (state) => state.precos);
export const selectTemplatesDocumento = createSelector(selectDocumentosState, (state) => state.templates);
export const selectSolicitacoesEmissao = createSelector(selectDocumentosState, (state) => state.solicitacoesEmissao);
export const selectPaginacaoSolicitacoesEmissao = createSelector(selectDocumentosState, (state) => state.paginacaoSolicitacoesEmissao);
export const selectUltimaCobrancaDocumento = createSelector(selectDocumentosState, (state) => state.ultimaCobranca);
export const selectSolicitacoesEscolaStaff = createSelector(selectDocumentosState, (state) => state.solicitacoesEscolaStaff);
export const selectPaginacaoSolicitacoesEscolaStaff = createSelector(selectDocumentosState, (state) => state.paginacaoSolicitacoesEscolaStaff);
export const selectMinhasSolicitacoesEscola = createSelector(selectDocumentosState, (state) => state.minhasSolicitacoesEscola);
export const selectDocumentosMensagem = createSelector(selectDocumentosState, (state) => state.mensagem);
export const selectDocumentosError = createSelector(selectDocumentosState, (state) => state.erro);
