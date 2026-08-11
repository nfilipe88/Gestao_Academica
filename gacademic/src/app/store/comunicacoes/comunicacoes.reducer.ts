import { createReducer, on } from '@ngrx/store';
import * as ComunicacoesActions from './comunicacoes.actions';
import { Comunicado } from './comunicacoes.models';

export interface ComunicacoesState {
  comunicados: Comunicado[];
  erro: string | null;
}

export const initialState: ComunicacoesState = {
  comunicados: [],
  erro: null
};

export const comunicacoesReducer = createReducer(
  initialState,
  on(ComunicacoesActions.carregarComunicados, ComunicacoesActions.criarComunicado,
    (state) => ({ ...state, erro: null })
  ),
  on(ComunicacoesActions.carregarComunicadosSucesso, (state, { comunicados }) => ({ ...state, comunicados })),
  on(ComunicacoesActions.comunicacoesOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
