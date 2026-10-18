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

// Disparada pelo authGuard (token já expirado antes de navegar) ou pelo
// jwtInterceptor (um 401 chegou a meio da sessão, ex.: token expirou
// enquanto o utilizador estava parado numa página) — ao contrário de
// logout(), fica com uma mensagem para mostrar no ecrã de login.
export const sessaoExpirada = createAction('[Auth] Sessão Expirada');

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

// Access token novo para a sessão já iniciada (refresh automático no
// jwtInterceptor, ou a sessão reemitida ao mudar a palavra-passe no
// Perfil, que termina todas as anteriores) — sem isto, o token antigo
// continuava na Store e cada pedido seguinte voltava a dar 401.
export const tokenRenovado = createAction(
  '[Auth] Token Renovado',
  props<{ token: string }>()
);

// Verificação em dois passos (código por e-mail): a palavra-passe estava
// certa mas a conta tem a verificação ligada — o login só termina com o
// código (POST /api/v1/auth/login/dois-fatores).
export const loginRequerDoisFatores = createAction(
  '[Auth API] Login Requer Dois Fatores',
  props<{ desafio: string; emailMascarado: string }>()
);
export const confirmarCodigoDoisFatores = createAction(
  '[Auth Página] Confirmar Código Dois Fatores',
  props<{ codigo: string }>()
);
export const reenviarCodigoDoisFatores = createAction('[Auth Página] Reenviar Código Dois Fatores');
export const codigoDoisFatoresReenviado = createAction(
  '[Auth API] Código Dois Fatores Reenviado',
  props<{ mensagem: string }>()
);
export const cancelarDoisFatores = createAction('[Auth Página] Cancelar Dois Fatores');
