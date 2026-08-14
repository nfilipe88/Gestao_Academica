import { createReducer, on } from '@ngrx/store';
import * as IndicadoresActions from './indicadores.actions';
import { Indicadores } from './indicadores.models';

export interface IndicadoresState {
  indicadores: Indicadores | null;
  erro: string | null;
}

export const initialState: IndicadoresState = {
  indicadores: null,
  erro: null
};

export const indicadoresReducer = createReducer(
  initialState,
  on(IndicadoresActions.carregarIndicadores, (state) => ({ ...state, erro: null })),
  on(IndicadoresActions.carregarIndicadoresSucesso, (state, { indicadores }) => ({ ...state, indicadores })),
  on(IndicadoresActions.indicadoresOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
