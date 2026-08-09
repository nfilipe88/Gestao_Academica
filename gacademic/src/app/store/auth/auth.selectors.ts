import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AuthState } from './auth.reducer';

export const selectAuthState = createFeatureSelector<AuthState>('auth');

export const selectToken = createSelector(
  selectAuthState,
  (state) => state.token
);

export const selectAuthError = createSelector(
  selectAuthState,
  (state) => state.erro
);

export const selectTenantId = createSelector(
  selectAuthState,
  (state) => state.usuario?.tenant_id
);

export const selectIsGestor = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso === 'GESTOR'
);
