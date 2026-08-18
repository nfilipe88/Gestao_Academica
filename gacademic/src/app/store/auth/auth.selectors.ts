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

// Portal do Aluno/Responsável: estes logins só têm acesso à sua própria
// visão de leitura (app/api/v1/portal.py) — nenhum dos módulos internos
// (Académico, Alunos, Diário, Horários, Comunicações, CRM, Financeiro,
// Professores) os deixa entrar (ver exigir_perfil_staff no back-end).
export const selectIsAlunoOuResponsavel = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso === 'ALUNO' || state.usuario?.perfil_acesso === 'RESPONSAVEL'
);

// Painel Super Admin: gere as instituições (tenants) em si, não os
// dados académicos de nenhuma — não tem acesso a nenhum módulo interno
// (ver exigir_perfil_staff no back-end).
export const selectIsSuperAdmin = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso === 'SUPER_ADMIN'
);

// Mapa de Permissões (/admin/permissoes): SUPER_ADMIN e GESTOR podem ver
// e editar (exigir_perfil("SUPER_ADMIN", "GESTOR") em api/v1/permissoes.py).
export const selectPodeEditarPermissoes = createSelector(
  selectAuthState,
  (state) => state.usuario?.perfil_acesso === 'SUPER_ADMIN' || state.usuario?.perfil_acesso === 'GESTOR'
);
