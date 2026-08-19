import { createReducer, on } from '@ngrx/store';
import * as PropinasActions from './propinas.actions';
import { LinhaPropina } from './propinas.models';

export interface PropinasState {
  linhas: LinhaPropina[];
  erro: string | null;
}

export const initialState: PropinasState = {
  linhas: [],
  erro: null
};

export const propinasReducer = createReducer(
  initialState,
  on(PropinasActions.carregarPropinas, PropinasActions.definirPropina,
    (state) => ({ ...state, erro: null })
  ),
  on(PropinasActions.carregarPropinasSucesso, (state, { linhas }) => ({ ...state, linhas })),
  on(PropinasActions.definirPropinaSucesso, (state, { linha }) => ({
    ...state,
    linhas: state.linhas.map(l => l.serie_ano_id === linha.serie_ano_id ? linha : l)
  })),
  on(PropinasActions.apagarPropinaSucesso, (state, { serie_ano_id }) => ({
    ...state,
    linhas: state.linhas.map(l => l.serie_ano_id === serie_ano_id
      ? { ...l, propina_id: null, valor_mensalidade: null, valor_matricula: null }
      : l)
  })),
  on(PropinasActions.propinasOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
