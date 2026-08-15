import { createReducer, on } from '@ngrx/store';
import * as ProfessoresActions from './professores.actions';
import { Alocacao, Professor } from './professores.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface ProfessoresState {
  professores: Professor[];
  paginacaoProfessores: EstadoPaginacao;
  alocacoes: Alocacao[];
  erro: string | null;
}

export const initialState: ProfessoresState = {
  professores: [],
  paginacaoProfessores: PAGINACAO_INICIAL,
  alocacoes: [],
  erro: null
};

export const professoresReducer = createReducer(
  initialState,
  on(ProfessoresActions.carregarProfessores, ProfessoresActions.criarProfessor,
     ProfessoresActions.carregarAlocacoes, ProfessoresActions.criarAlocacao,
    (state) => ({ ...state, erro: null })
  ),
  on(ProfessoresActions.carregarProfessoresSucesso, (state, { professores, paginacao }) => ({ ...state, professores, paginacaoProfessores: paginacao })),
  on(ProfessoresActions.carregarAlocacoesSucesso, (state, { alocacoes }) => ({ ...state, alocacoes })),
  on(ProfessoresActions.professoresOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
