import { createReducer, on } from '@ngrx/store';
import * as DiarioActions from './diario.actions';
import { AlunoDiario, ConsolidadoTurmaDisciplina, PeriodoAvaliacao } from './diario.models';

export interface DiarioState {
  alunos: AlunoDiario[];
  consolidado: ConsolidadoTurmaDisciplina | null;
  periodos: PeriodoAvaliacao[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: DiarioState = {
  alunos: [],
  consolidado: null,
  periodos: [],
  mensagem: null,
  erro: null
};

export const diarioReducer = createReducer(
  initialState,
  on(DiarioActions.carregarAlunosDiario, DiarioActions.lancarFrequencias,
     DiarioActions.lancarNotas, DiarioActions.carregarConsolidado,
     DiarioActions.carregarPeriodos, DiarioActions.criarPeriodo,
     DiarioActions.trancarPeriodo, DiarioActions.reabrirPeriodo,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(DiarioActions.carregarAlunosDiarioSucesso, (state, { alunos }) => ({ ...state, alunos })),
  on(DiarioActions.carregarConsolidadoSucesso, (state, { consolidado }) => ({ ...state, consolidado })),
  on(DiarioActions.carregarPeriodosSucesso, (state, { periodos }) => ({ ...state, periodos })),
  on(DiarioActions.diarioOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(DiarioActions.diarioOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
