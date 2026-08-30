import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AdminState } from './admin.reducer';

export const selectAdminState = createFeatureSelector<AdminState>('admin');

export const selectTenants = createSelector(selectAdminState, (state) => state.tenants);
export const selectPaginacaoTenants = createSelector(selectAdminState, (state) => state.paginacaoTenants);
export const selectAdminMensagem = createSelector(selectAdminState, (state) => state.mensagem);
export const selectAdminError = createSelector(selectAdminState, (state) => state.erro);

export const selectPlanos = createSelector(selectAdminState, (state) => state.planos);
export const selectPlanosAtivos = createSelector(selectPlanos, (planos) => planos.filter(p => p.ativo));
export const selectMrr = createSelector(selectAdminState, (state) => state.mrr);
export const selectAssinaturasPorTenant = createSelector(selectAdminState, (state) => state.assinaturasPorTenant);

export const selectTicketsAdmin = createSelector(selectAdminState, (state) => state.tickets);
export const selectPaginacaoTicketsAdmin = createSelector(selectAdminState, (state) => state.paginacaoTickets);
export const selectTicketAtualAdmin = createSelector(selectAdminState, (state) => state.ticketAtual);
