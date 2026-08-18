import { createReducer, on } from '@ngrx/store';
import * as PermissoesActions from './permissoes.actions';
import { PermissaoModulo } from './permissoes.models';

export interface PermissoesState {
  permissoes: PermissaoModulo[];
  erro: string | null;
}

export const initialState: PermissoesState = {
  permissoes: [],
  erro: null
};

export const permissoesReducer = createReducer(
  initialState,
  on(PermissoesActions.carregarPermissoes, PermissoesActions.atualizarPermissao,
    (state) => ({ ...state, erro: null })
  ),
  on(PermissoesActions.carregarPermissoesSucesso, (state, { permissoes }) => ({ ...state, permissoes })),
  on(PermissoesActions.atualizarPermissaoSucesso, (state, { permissao }) => ({
    ...state,
    permissoes: state.permissoes.map(p => p.id === permissao.id ? permissao : p)
  })),
  on(PermissoesActions.permissoesOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
