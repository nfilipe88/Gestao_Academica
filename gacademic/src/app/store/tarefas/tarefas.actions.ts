import { createAction, props } from '@ngrx/store';
import { AvaliacaoAlunoInput, Tarefa, TarefaComAvaliacoes } from './tarefas.models';

export const carregarTarefas = createAction(
  '[Tarefas] Carregar Tarefas',
  props<{ turma_id: string, disciplina_id: string }>()
);
export const carregarTarefasSucesso = createAction(
  '[Tarefas] Carregar Tarefas Sucesso',
  props<{ tarefas: Tarefa[] }>()
);

export const criarTarefa = createAction(
  '[Tarefas] Criar Tarefa',
  props<{
    alocacao_id: string, titulo: string, descricao: string | null,
    data_entrega: string, valor_maximo: number, periodo_avaliacao: string | null,
    turma_id: string, disciplina_id: string
  }>()
);

export const carregarTarefaDetalhe = createAction(
  '[Tarefas] Carregar Tarefa Detalhe',
  props<{ tarefa_id: string }>()
);
export const carregarTarefaDetalheSucesso = createAction(
  '[Tarefas] Carregar Tarefa Detalhe Sucesso',
  props<{ tarefa: TarefaComAvaliacoes }>()
);
export const fecharTarefaDetalhe = createAction('[Tarefas] Fechar Tarefa Detalhe');

export const avaliarTarefa = createAction(
  '[Tarefas] Avaliar Tarefa',
  props<{ tarefa_id: string, avaliacoes: AvaliacaoAlunoInput[] }>()
);

export const tarefasOperacaoSucesso = createAction(
  '[Tarefas] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const tarefasOperacaoFalhou = createAction(
  '[Tarefas API] Operação Falhou',
  props<{ erro: string }>()
);
