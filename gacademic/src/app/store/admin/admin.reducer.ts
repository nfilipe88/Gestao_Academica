import { createReducer, on } from '@ngrx/store';
import * as AdminActions from './admin.actions';
import { AssinaturaTenant, PlanoSaaS, ResumoMrr, TenantResumo, TicketAdminComMensagens, TicketAdminRegisto } from './admin.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface AdminState {
  tenants: TenantResumo[];
  paginacaoTenants: EstadoPaginacao;
  mensagem: string | null;
  erro: string | null;
  planos: PlanoSaaS[];
  mrr: ResumoMrr | null;
  // Assinatura da escola atualmente a ser vista/editada no painel de tenants.
  assinaturasPorTenant: Record<string, AssinaturaTenant | null>;
  tickets: TicketAdminRegisto[];
  paginacaoTickets: EstadoPaginacao;
  ticketAtual: TicketAdminComMensagens | null;
}

export const initialState: AdminState = {
  tenants: [],
  paginacaoTenants: PAGINACAO_INICIAL,
  mensagem: null,
  erro: null,
  planos: [],
  mrr: null,
  assinaturasPorTenant: {},
  tickets: [],
  paginacaoTickets: PAGINACAO_INICIAL,
  ticketAtual: null,
};

export const adminReducer = createReducer(
  initialState,
  on(AdminActions.carregarTenants, AdminActions.criarTenant, AdminActions.atualizarStatusTenant,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(AdminActions.carregarTenantsSucesso, (state, { tenants, paginacao }) => ({ ...state, tenants, paginacaoTenants: paginacao })),
  on(AdminActions.adminOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(AdminActions.adminOperacaoFalhou, (state, { erro }) => ({ ...state, erro })),

  on(AdminActions.carregarPlanosSucesso, (state, { planos }) => ({ ...state, planos })),
  on(AdminActions.carregarMrrSucesso, (state, { mrr }) => ({ ...state, mrr })),
  on(AdminActions.carregarAssinaturaTenantSucesso, (state, { tenant_id, assinatura }) => ({
    ...state,
    assinaturasPorTenant: { ...state.assinaturasPorTenant, [tenant_id]: assinatura }
  })),

  on(AdminActions.carregarTicketsAdminSucesso, (state, { tickets, paginacao }) => ({ ...state, tickets, paginacaoTickets: paginacao })),
  on(AdminActions.carregarTicketAdminSucesso, (state, { ticket }) => ({ ...state, ticketAtual: ticket }))
);
