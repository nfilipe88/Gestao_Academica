import { createFeatureSelector, createSelector } from '@ngrx/store';
import { DiarioState } from './diario.reducer';

export const selectDiarioState = createFeatureSelector<DiarioState>('diario');

export const selectAlunosDiario = createSelector(
  selectDiarioState,
  (state) => state.alunos
);

export const selectConsolidado = createSelector(
  selectDiarioState,
  (state) => state.consolidado
);

export const selectPeriodos = createSelector(
  selectDiarioState,
  (state) => state.periodos
);

export const selectAvaliacoes = createSelector(
  selectDiarioState,
  (state) => state.avaliacoes
);

export const selectNotasAvaliacaoSelecionada = createSelector(
  selectDiarioState,
  (state) => state.notasAvaliacaoSelecionada
);

export const selectNotasFinais = createSelector(
  selectDiarioState,
  (state) => state.notasFinais
);

export const selectDiarioMensagem = createSelector(
  selectDiarioState,
  (state) => state.mensagem
);

export const selectDiarioError = createSelector(
  selectDiarioState,
  (state) => state.erro
);
