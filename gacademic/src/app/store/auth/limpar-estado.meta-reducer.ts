import { ActionReducer } from '@ngrx/store';
import { logout, sessaoExpirada } from './auth.actions';

/**
 * Ao terminar (logout) ou perder (sessão expirada) a sessão, repõe TODOS os
 * slices do NgRx ao estado inicial. Sem isto, os dados do utilizador anterior
 * (alunos, faturas, notas, notificações…) ficavam na memória do separador e
 * eram visíveis a quem iniciasse sessão a seguir sem recarregar a página.
 *
 * O próprio reducer da auth volta a correr sobre o estado inicial com a ação
 * original, por isso a mensagem de "sessão expirada" no ecrã de login mantém-se.
 */
export function limparEstadoNoLogout<S>(reducer: ActionReducer<S>): ActionReducer<S> {
  return (state, action) => {
    if (action.type === logout.type || action.type === sessaoExpirada.type) {
      state = undefined;
    }
    return reducer(state, action);
  };
}
