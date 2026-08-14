import { createFeatureSelector, createSelector } from '@ngrx/store';
import { TarefasState } from './tarefas.reducer';

export const selectTarefasState = createFeatureSelector<TarefasState>('tarefas');

export const selectTarefas = createSelector(selectTarefasState, (state) => state.tarefas);
export const selectTarefaDetalhe = createSelector(selectTarefasState, (state) => state.tarefaDetalhe);
export const selectTarefasMensagem = createSelector(selectTarefasState, (state) => state.mensagem);
export const selectTarefasError = createSelector(selectTarefasState, (state) => state.erro);
