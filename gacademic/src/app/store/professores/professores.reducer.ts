import { createReducer, on } from '@ngrx/store';
import * as ProfessoresActions from './professores.actions';
import { Professor } from './professores.models';

export interface ProfessoresState {
  professores: Professor[];
  erro: string | null;
}

export const initialState: ProfessoresState = {
  professores: [],
  erro: null
};

export const professoresReducer = createReducer(
  initialState,
  on(ProfessoresActions.carregarProfessores, ProfessoresActions.criarProfessor,
    (state) => ({ ...state, erro: null })
  ),
  on(ProfessoresActions.carregarProfessoresSucesso, (state, { professores }) => ({ ...state, professores })),
  on(ProfessoresActions.professoresOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
