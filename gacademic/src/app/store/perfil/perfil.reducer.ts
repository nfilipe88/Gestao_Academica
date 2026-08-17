import { createReducer, on } from '@ngrx/store';
import * as PerfilActions from './perfil.actions';
import { Perfil } from './perfil.models';

export interface PerfilState {
  perfil: Perfil | null;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: PerfilState = {
  perfil: null,
  mensagem: null,
  erro: null,
};

export const perfilReducer = createReducer(
  initialState,
  on(PerfilActions.carregarPerfilSucesso, (state, { perfil }) => ({
    ...state, perfil, erro: null,
  })),
  on(PerfilActions.perfilOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(PerfilActions.perfilOperacaoFalhou, (state, { erro }) => ({ ...state, erro })),
  on(PerfilActions.limparMensagensPerfil, (state) => ({ ...state, mensagem: null, erro: null }))
);
