import { createReducer, on } from '@ngrx/store';
import * as AuthActions from './auth.actions';
import { UsuarioLogado } from './auth.actions';

export interface AuthState {
  token: string | null;
  usuario: UsuarioLogado | null;
  isAuthenticated: boolean;
  erro: string | null;
}

// Estado inicial agora é limpo (seguro para o Node.js / SSR)
export const initialState: AuthState = {
  token: null,
  usuario: null,
  isAuthenticated: false,
  erro: null
};

export const authReducer = createReducer(
  initialState,
  on(AuthActions.iniciarLogin, (state) => ({
    ...state,
    erro: null
  })),
  on(AuthActions.loginSuccess, (state, { token, usuario }) => ({
    ...state,
    token,
    usuario,
    isAuthenticated: true,
    erro: null
  })),
  on(AuthActions.loginFalhou, (state, { erro }) => ({
    ...state,
    erro
  })),
  on(AuthActions.logout, (state) => ({
    ...state,
    token: null,
    usuario: null,
    isAuthenticated: false,
    erro: null
  })),
  // Nova ação para restaurar os dados quando o utilizador faz "F5"
  on(AuthActions.restoreAuth, (state, { token, usuario }) => ({
    ...state,
    token,
    usuario,
    isAuthenticated: !!token
  }))
);
