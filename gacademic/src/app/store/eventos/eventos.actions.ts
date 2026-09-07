import { createAction, props } from '@ngrx/store';
import { Evento } from './eventos.models';

export const carregarEventos = createAction('[Eventos] Carregar Eventos');
export const carregarEventosSucesso = createAction(
  '[Eventos] Carregar Eventos Sucesso',
  props<{ eventos: Evento[] }>()
);

export const criarEvento = createAction(
  '[Eventos] Criar Evento',
  props<{ titulo: string; data: string; descricao: string | null; publicado: boolean }>()
);

export const atualizarEvento = createAction(
  '[Eventos] Atualizar Evento',
  props<{ evento_id: string; titulo: string; data: string; descricao: string | null; publicado: boolean }>()
);

export const removerEvento = createAction(
  '[Eventos] Remover Evento',
  props<{ evento_id: string }>()
);

export const adicionarFotoEvento = createAction(
  '[Eventos] Adicionar Foto Evento',
  props<{ evento_id: string; ficheiro: File }>()
);

export const removerFotoEvento = createAction(
  '[Eventos] Remover Foto Evento',
  props<{ evento_id: string; foto_id: string }>()
);

export const eventosOperacaoSucesso = createAction(
  '[Eventos] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const eventosOperacaoFalhou = createAction(
  '[Eventos API] Operação Falhou',
  props<{ erro: string }>()
);
