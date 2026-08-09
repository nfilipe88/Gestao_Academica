import { createAction, props } from '@ngrx/store';
// import { UsuarioLogado } from './auth.reducer';

// Modelo da nossa interface de estado
export interface UsuarioLogado {
  id: string;
  tenant_id: string;
  nome_completo: string;
  perfil_acesso: string; // 'SUPER_ADMIN', 'GESTOR', 'PROFESSOR'
}

export const loginSuccess = createAction(
  '[Auth API] Login efetuado com Sucesso',
  props<{ token: string, usuario: UsuarioLogado }>()
);

export const logout = createAction('[Auth] Logout do Utilizador');

// Ação disparada pelo componente de ecrã
export const iniciarLogin = createAction(
  '[Auth Página] Iniciar Tentativa de Login',
  props<{ email: string; palavraPasse: string }>()
);

export const loginFalhou = createAction(
  '[Auth API] Login Falhou',
  props<{ erro: string }>()
);

// Ação para carregar os dados do localStorage para a Store ao abrir a app
export const restoreAuth = createAction(
  '[Auth Init] Restaurar Sessão do LocalStorage',
  props<{ token: string | null, usuario: UsuarioLogado | null }>()
);
