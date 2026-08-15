import { createAction, props } from '@ngrx/store';
import { Comunicado } from './comunicacoes.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

export const carregarComunicados = createAction(
  '[Comunicacoes] Carregar Comunicados',
  props<{ page?: number, page_size?: number }>()
);
export const carregarComunicadosSucesso = createAction(
  '[Comunicacoes] Carregar Comunicados Sucesso',
  props<{ comunicados: Comunicado[], paginacao: EstadoPaginacao }>()
);

export const criarComunicado = createAction(
  '[Comunicacoes] Criar Comunicado',
  props<{
    tipo: string,
    titulo: string,
    corpo: string,
    destinatario_tipo: string,
    destinatario_turma_id: string | null,
    destinatario_aluno_id: string | null
  }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const comunicacoesOperacaoFalhou = createAction(
  '[Comunicacoes API] Operação Falhou',
  props<{ erro: string }>()
);
