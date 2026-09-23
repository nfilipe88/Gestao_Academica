import { createFeatureSelector, createSelector } from '@ngrx/store';
import { LmsState } from './lms.reducer';

export const selectLmsState = createFeatureSelector<LmsState>('lms');

export const selectMateriais = createSelector(selectLmsState, (state) => state.materiais);
export const selectLmsMensagem = createSelector(selectLmsState, (state) => state.mensagem);
export const selectLmsError = createSelector(selectLmsState, (state) => state.erro);
export const selectASugerirConteudo = createSelector(selectLmsState, (state) => state.aSugerirConteudo);
export const selectSugestaoConteudo = createSelector(selectLmsState, (state) => state.sugestaoConteudo);
export const selectBancoQuestoes = createSelector(selectLmsState, (state) => state.bancoQuestoes);
export const selectGruposExame = createSelector(selectLmsState, (state) => state.grupos);
export const selectExameDetalhe = createSelector(selectLmsState, (state) => state.exameDetalhe);
export const selectResultadosPorGrupo = createSelector(selectLmsState, (state) => state.resultadosPorGrupo);
export const selectAtribuicoesPorGrupo = createSelector(selectLmsState, (state) => state.atribuicoesPorGrupo);
