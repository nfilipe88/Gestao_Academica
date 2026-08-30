import { createAction, props } from '@ngrx/store';
import { SolicitacaoTransferencia } from './transferencias.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

export const criarSolicitacao = createAction(
  '[Transferencias] Criar Solicitacao',
  props<{ aluno_id: string, nif_destino: string, motivo?: string }>()
);

// Três listas independentes (slices próprios no estado — ver
// transferencias.reducer.ts): "Enviados" (pedidos que esta escola fez,
// como origem), "Recebidos" (pedidos de OUTRAS escolas dirigidos a
// esta, onde a decisão de Aceitar/Negar acontece — ver
// app/api/v1/transferencias.py) e "Auditoria" (Super Admin, cross-tenant,
// só leitura). Terem estado próprio evita que recarregar uma clobbere
// a outra quando o componente mostra duas ao mesmo tempo em abas.
export const carregarMinhasSolicitacoes = createAction(
  '[Transferencias] Carregar Minhas Solicitacoes',
  props<{ page?: number, page_size?: number, status?: string, data_inicio?: string, data_fim?: string }>()
);
export const carregarEnviadasSucesso = createAction(
  '[Transferencias] Carregar Enviadas Sucesso',
  props<{ solicitacoes: SolicitacaoTransferencia[], paginacao: EstadoPaginacao }>()
);

export const carregarSolicitacoesRecebidas = createAction(
  '[Transferencias] Carregar Solicitacoes Recebidas',
  props<{ page?: number, page_size?: number }>()
);
export const carregarRecebidasSucesso = createAction(
  '[Transferencias] Carregar Recebidas Sucesso',
  props<{ solicitacoes: SolicitacaoTransferencia[], paginacao: EstadoPaginacao }>()
);

export const carregarSolicitacoesAuditoria = createAction(
  '[Transferencias] Carregar Solicitacoes Auditoria',
  props<{ page?: number, page_size?: number }>()
);
export const carregarAuditoriaSucesso = createAction(
  '[Transferencias] Carregar Auditoria Sucesso',
  props<{ solicitacoes: SolicitacaoTransferencia[], paginacao: EstadoPaginacao }>()
);

export const aprovarSolicitacao = createAction('[Transferencias] Aprovar Solicitacao', props<{ solicitacao_id: string }>());
export const rejeitarSolicitacao = createAction(
  '[Transferencias] Rejeitar Solicitacao',
  props<{ solicitacao_id: string, observacoes: string }>()
);

export const transferenciasOperacaoSucesso = createAction('[Transferencias] Operacao Sucesso', props<{ mensagem: string }>());
export const transferenciasOperacaoFalhou = createAction('[Transferencias API] Operação Falhou', props<{ erro: string }>());
