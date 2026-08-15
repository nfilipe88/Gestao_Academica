import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AdminState } from './admin.reducer';

export const selectAdminState = createFeatureSelector<AdminState>('admin');

export const selectTenants = createSelector(selectAdminState, (state) => state.tenants);
export const selectPaginacaoTenants = createSelector(selectAdminState, (state) => state.paginacaoTenants);
export const selectAdminMensagem = createSelector(selectAdminState, (state) => state.mensagem);
export const selectAdminError = createSelector(selectAdminState, (state) => state.erro);
