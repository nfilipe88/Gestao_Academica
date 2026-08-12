import { createFeatureSelector, createSelector } from '@ngrx/store';
import { FinanceiroState } from './financeiro.reducer';

export const selectFinanceiroState = createFeatureSelector<FinanceiroState>('financeiro');

export const selectMatriculasDoAluno = createSelector(selectFinanceiroState, (state) => state.matriculas);
export const selectResponsaveisElegiveis = createSelector(selectFinanceiroState, (state) => state.responsaveis);
export const selectContrato = createSelector(selectFinanceiroState, (state) => state.contrato);
export const selectContratoCarregado = createSelector(selectFinanceiroState, (state) => state.contratoCarregado);
export const selectFaturas = createSelector(selectFinanceiroState, (state) => state.faturas);
export const selectUltimaCobranca = createSelector(selectFinanceiroState, (state) => state.ultimaCobranca);
export const selectFinanceiroMensagem = createSelector(selectFinanceiroState, (state) => state.mensagem);
export const selectFinanceiroError = createSelector(selectFinanceiroState, (state) => state.erro);
