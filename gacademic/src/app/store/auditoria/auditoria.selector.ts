import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AuditoriaState } from './auditoria.reducer';

export const selectAuditoriaState = createFeatureSelector<AuditoriaState>('auditoria');

export const selectAuditoriaRegistos = createSelector(selectAuditoriaState, (state) => state.registos);
export const selectAuditoriaPaginacao = createSelector(selectAuditoriaState, (state) => state.paginacao);
export const selectAuditoriaEntidades = createSelector(selectAuditoriaState, (state) => state.entidades);
export const selectAuditoriaErro = createSelector(selectAuditoriaState, (state) => state.erro);
