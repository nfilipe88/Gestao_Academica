import { createFeatureSelector, createSelector } from '@ngrx/store';
import { CrmState } from './crm.reducer';

export const selectCrmState = createFeatureSelector<CrmState>('crm');

export const selectEtapas = createSelector(selectCrmState, (state) => state.etapas);
export const selectOportunidades = createSelector(selectCrmState, (state) => state.oportunidades);
export const selectCrmMensagem = createSelector(selectCrmState, (state) => state.mensagem);
export const selectCrmError = createSelector(selectCrmState, (state) => state.erro);
