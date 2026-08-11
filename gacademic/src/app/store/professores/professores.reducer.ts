import { createReducer, on } from '@ngrx/store';
import * as ProfessoresActions from './professores.actions';
import { Alocacao, Professor } from './professores.models';

export interface ProfessoresState {
  professores: Professor[];
  alocacoes: Alocacao[];
  erro: string | null;
}

export const initialState: ProfessoresState = {
  professores: [],
  alocacoes: [],
  erro: null
};

export const professoresReducer = createReducer(
  initialState,
  on(ProfessoresActions.carregarProfessores, ProfessoresActions.criarProfessor,
     ProfessoresActions.carregarAlocacoes, ProfessoresActions.criarAlocacao,
    (state) => ({ ...state, erro: null })
  ),
  on(ProfessoresActions.carregarProfessoresSucesso, (state, { professores }) => ({ ...state, professores })),
  on(ProfessoresActions.carregarAlocacoesSucesso, (state, { alocacoes }) => ({ ...state, alocacoes })),
  on(ProfessoresActions.professoresOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
