import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AlunosState } from './alunos.reducer';

export const selectAlunosState = createFeatureSelector<AlunosState>('alunos');

export const selectAlunos = createSelector(
  selectAlunosState,
  (state) => state.alunos
);

export const selectPaginacaoAlunos = createSelector(
  selectAlunosState,
  (state) => state.paginacaoAlunos
);

export const selectResponsaveis = createSelector(
  selectAlunosState,
  (state) => state.responsaveis
);

export const selectPaginacaoResponsaveis = createSelector(
  selectAlunosState,
  (state) => state.paginacaoResponsaveis
);

export const selectVinculos = createSelector(
  selectAlunosState,
  (state) => state.vinculos
);

export const selectAlunosMensagem = createSelector(
  selectAlunosState,
  (state) => state.mensagem
);

export const selectAlunosError = createSelector(
  selectAlunosState,
  (state) => state.erro
);
