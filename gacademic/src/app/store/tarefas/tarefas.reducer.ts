import { createReducer, on } from '@ngrx/store';
import * as TarefasActions from './tarefas.actions';
import { Tarefa, TarefaComAvaliacoes } from './tarefas.models';

export interface TarefasState {
  tarefas: Tarefa[];
  tarefaDetalhe: TarefaComAvaliacoes | null;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: TarefasState = {
  tarefas: [],
  tarefaDetalhe: null,
  mensagem: null,
  erro: null
};

export const tarefasReducer = createReducer(
  initialState,
  on(TarefasActions.carregarTarefas, TarefasActions.criarTarefa,
     TarefasActions.carregarTarefaDetalhe, TarefasActions.avaliarTarefa,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(TarefasActions.carregarTarefasSucesso, (state, { tarefas }) => ({ ...state, tarefas })),
  on(TarefasActions.carregarTarefaDetalheSucesso, (state, { tarefa }) => ({ ...state, tarefaDetalhe: tarefa })),
  on(TarefasActions.fecharTarefaDetalhe, (state) => ({ ...state, tarefaDetalhe: null })),
  on(TarefasActions.tarefasOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(TarefasActions.tarefasOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
