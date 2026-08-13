import { createFeatureSelector, createSelector } from '@ngrx/store';
import { HorariosState } from './horarios.reducer';

export const selectHorariosState = createFeatureSelector<HorariosState>('horarios');

export const selectGradeDaTurma = createSelector(
  selectHorariosState,
  (state) => state.gradeDaTurma
);

export const selectMinhaGrade = createSelector(
  selectHorariosState,
  (state) => state.minhaGrade
);

export const selectHorariosMensagem = createSelector(
  selectHorariosState,
  (state) => state.mensagem
);

export const selectHorariosError = createSelector(
  selectHorariosState,
  (state) => state.erro
);
