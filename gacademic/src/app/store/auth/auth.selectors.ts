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

export const selectUsuario = createSelector(
  selectAuthState,
  (state) => state.usuario
);

export const selectTenantId = createSelector(
  selectAuthState,
  (state) => state.usuario?.tenant_id
);

export const selectIsGestor = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso === 'GESTOR'
);

export const selectPerfilAcesso = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso ?? null
);

// Usado pelo módulo Financeiro: criar contrato, marcar fatura paga e
// processar a régua de cobrança são GESTOR/SECRETARIA no back-end
// (exigir_perfil("GESTOR", "SECRETARIA") em financeiro.py).
export const selectIsGestorOuSecretaria = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso === 'GESTOR' || state.usuario?.perfil_acesso === 'SECRETARIA'
);
