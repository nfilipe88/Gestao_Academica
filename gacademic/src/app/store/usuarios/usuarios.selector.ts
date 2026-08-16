import { createFeatureSelector, createSelector } from '@ngrx/store';
import { UsuariosState } from './usuarios.reducer';

export const selectUsuariosState = createFeatureSelector<UsuariosState>('usuarios');

export const selectUsuarios = createSelector(selectUsuariosState, (state) => state.usuarios);
export const selectPaginacaoUsuarios = createSelector(selectUsuariosState, (state) => state.paginacaoUsuarios);
export const selectUsuariosAuditoria = createSelector(selectUsuariosState, (state) => state.auditoria);
export const selectPaginacaoAuditoria = createSelector(selectUsuariosState, (state) => state.paginacaoAuditoria);
export const selectUsuariosMensagem = createSelector(selectUsuariosState, (state) => state.mensagem);
export const selectUsuariosError = createSelector(selectUsuariosState, (state) => state.erro);
