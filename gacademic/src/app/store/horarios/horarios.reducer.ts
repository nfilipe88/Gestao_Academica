import { createReducer, on } from '@ngrx/store';
import * as HorariosActions from './horarios.actions';
import { AulaPorLancar, HorarioAula } from './horarios.models';

export interface HorariosState {
  gradeDaTurma: HorarioAula[];
  minhaGrade: HorarioAula[];
  gradeDoProfessor: HorarioAula[];
  aulasPorLancar: AulaPorLancar[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: HorariosState = {
  gradeDaTurma: [],
  minhaGrade: [],
  gradeDoProfessor: [],
  aulasPorLancar: [],
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
  on(HorariosActions.carregarGradeDoProfessorSucesso, (state, { horarios }) => ({ ...state, gradeDoProfessor: horarios })),
  on(HorariosActions.limparGradeDoProfessor, (state) => ({ ...state, gradeDoProfessor: [] })),
  on(HorariosActions.carregarAulasPorLancarSucesso, (state, { aulas }) => ({ ...state, aulasPorLancar: aulas })),
  on(HorariosActions.horariosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(HorariosActions.horariosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
