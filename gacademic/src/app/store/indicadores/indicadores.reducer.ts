import { createReducer, on } from '@ngrx/store';
import * as IndicadoresActions from './indicadores.actions';
import { AlunoRisco, Indicadores } from './indicadores.models';

export interface IndicadoresState {
  indicadores: Indicadores | null;
  alunosEmRisco: AlunoRisco[] | null;
  erro: string | null;
}

export const initialState: IndicadoresState = {
  indicadores: null,
  alunosEmRisco: null,
  erro: null
};

export const indicadoresReducer = createReducer(
  initialState,
  on(IndicadoresActions.carregarIndicadores, IndicadoresActions.carregarRiscoEvasao, (state) => ({ ...state, erro: null })),
  on(IndicadoresActions.carregarIndicadoresSucesso, (state, { indicadores }) => ({ ...state, indicadores })),
  on(IndicadoresActions.carregarRiscoEvasaoSucesso, (state, { alunosEmRisco }) => ({ ...state, alunosEmRisco })),
  on(IndicadoresActions.indicadoresOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
