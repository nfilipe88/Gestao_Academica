import { createFeatureSelector, createSelector } from '@ngrx/store';
import { LmsState } from './lms.reducer';

export const selectLmsState = createFeatureSelector<LmsState>('lms');

export const selectMateriais = createSelector(selectLmsState, (state) => state.materiais);
export const selectLmsMensagem = createSelector(selectLmsState, (state) => state.mensagem);
export const selectLmsError = createSelector(selectLmsState, (state) => state.erro);
export const selectASugerirConteudo = createSelector(selectLmsState, (state) => state.aSugerirConteudo);
export const selectSugestaoConteudo = createSelector(selectLmsState, (state) => state.sugestaoConteudo);
export const selectBancoQuestoes = createSelector(selectLmsState, (state) => state.bancoQuestoes);
export const selectExames = createSelector(selectLmsState, (state) => state.exames);
export const selectExameDetalhe = createSelector(selectLmsState, (state) => state.exameDetalhe);
export const selectResultadosPorExame = createSelector(selectLmsState, (state) => state.resultadosPorExame);
