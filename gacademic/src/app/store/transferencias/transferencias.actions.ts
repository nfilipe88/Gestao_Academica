import { createAction, props } from '@ngrx/store';
import { SolicitacaoTransferencia } from './transferencias.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

export const criarSolicitacao = createAction(
  '[Transferencias] Criar Solicitacao',
  props<{ aluno_id: string, nif_destino: string, motivo?: string }>()
);

export const carregarMinhasSolicitacoes = createAction(
  '[Transferencias] Carregar Minhas Solicitacoes',
  props<{ page?: number, page_size?: number }>()
);
export const carregarSolicitacoesSuperAdmin = createAction(
  '[Transferencias] Carregar Solicitacoes Super Admin',
  props<{ page?: number, page_size?: number }>()
);
export const carregarSolicitacoesSucesso = createAction(
  '[Transferencias] Carregar Solicitacoes Sucesso',
  props<{ solicitacoes: SolicitacaoTransferencia[], paginacao: EstadoPaginacao }>()
);

export const aprovarSolicitacao = createAction('[Transferencias] Aprovar Solicitacao', props<{ solicitacao_id: string }>());
export const rejeitarSolicitacao = createAction(
  '[Transferencias] Rejeitar Solicitacao',
  props<{ solicitacao_id: string, observacoes: string }>()
);

export const transferenciasOperacaoSucesso = createAction('[Transferencias] Operacao Sucesso', props<{ mensagem: string }>());
export const transferenciasOperacaoFalhou = createAction('[Transferencias API] Operação Falhou', props<{ erro: string }>());
