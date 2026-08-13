import { createReducer, on } from '@ngrx/store';
import * as HorariosActions from './horarios.actions';
import { HorarioAula } from './horarios.models';

export interface HorariosState {
  gradeDaTurma: HorarioAula[];
  minhaGrade: HorarioAula[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: HorariosState = {
  gradeDaTurma: [],
  minhaGrade: [],
  mensagem: null,
  erro: null
};

export const horariosReducer = createReducer(
  initialState,
  on(HorariosActions.carregarGradeDaTurma, HorariosActions.carregarMinhaGrade,
     HorariosActions.criarHorario, HorariosActions.atualizarHorario, HorariosActions.removerHorario,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(HorariosActions.carregarGradeDaTurmaSucesso, (state, { horarios }) => ({ ...state, gradeDaTurma: horarios })),
  on(HorariosActions.carregarMinhaGradeSucesso, (state, { horarios }) => ({ ...state, minhaGrade: horarios })),
  on(HorariosActions.horariosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(HorariosActions.horariosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
