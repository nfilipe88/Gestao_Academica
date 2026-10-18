import { createReducer, on } from '@ngrx/store';
import * as AuthActions from './auth.actions';
import { UsuarioLogado } from './auth.actions';

export interface DoisFatoresPendente {
  desafio: string;
  emailMascarado: string;
  aviso: string | null;
}

export interface AuthState {
  token: string | null;
  usuario: UsuarioLogado | null;
  isAuthenticated: boolean;
  erro: string | null;
  // Segundo passo do login em curso (verificação em dois passos por e-mail).
  doisFatores: DoisFatoresPendente | null;
}

// Estado inicial agora é limpo (seguro para o Node.js / SSR)
export const initialState: AuthState = {
  token: null,
  usuario: null,
  isAuthenticated: false,
  erro: null,
  doisFatores: null
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
    erro: null,
    doisFatores: null
  })),
  on(AuthActions.loginRequerDoisFatores, (state, { desafio, emailMascarado }) => ({
    ...state,
    erro: null,
    doisFatores: { desafio, emailMascarado, aviso: null }
  })),
  on(AuthActions.confirmarCodigoDoisFatores, AuthActions.reenviarCodigoDoisFatores, (state) => ({
    ...state,
    erro: null,
    doisFatores: state.doisFatores ? { ...state.doisFatores, aviso: null } : null
  })),
  on(AuthActions.codigoDoisFatoresReenviado, (state, { mensagem }) => ({
    ...state,
    doisFatores: state.doisFatores ? { ...state.doisFatores, aviso: mensagem } : null
  })),
  on(AuthActions.cancelarDoisFatores, (state) => ({
    ...state,
    erro: null,
    doisFatores: null
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
  on(AuthActions.sessaoExpirada, (state) => ({
    ...state,
    token: null,
    usuario: null,
    isAuthenticated: false,
    erro: 'A sua sessão expirou. Inicie sessão novamente.'
  })),
  // Nova ação para restaurar os dados quando o utilizador faz "F5"
  on(AuthActions.restoreAuth, (state, { token, usuario }) => ({
    ...state,
    token,
    usuario,
    isAuthenticated: !!token
  })),
  on(AuthActions.tokenRenovado, (state, { token }) => ({
    ...state,
    token
  }))
);
