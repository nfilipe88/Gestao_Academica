import { createAction, props } from '@ngrx/store';
import { TicketComMensagens, TicketRegisto } from './suporte.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

// "Meus tickets" — a própria escola (Gestor/Secretaria), sempre a
// própria escola do token (sem tenant_id: ao contrário de
// store/usuarios e store/auditoria, os tickets do Super Admin vivem
// numa vista cross-tenant à parte, ver store/admin).

export const carregarMeusTickets = createAction(
  '[Suporte] Carregar Meus Tickets',
  props<{ page?: number; page_size?: number }>()
);
export const carregarMeusTicketsSucesso = createAction(
  '[Suporte] Carregar Meus Tickets Sucesso',
  props<{ tickets: TicketRegisto[]; paginacao: EstadoPaginacao }>()
);

export const criarTicket = createAction(
  '[Suporte] Criar Ticket',
  props<{ nome: string; email: string; assunto: string; mensagem: string }>()
);

export const carregarTicket = createAction(
  '[Suporte] Carregar Ticket',
  props<{ id: string }>()
);
export const carregarTicketSucesso = createAction(
  '[Suporte] Carregar Ticket Sucesso',
  props<{ ticket: TicketComMensagens }>()
);

export const enviarMensagemTicket = createAction(
  '[Suporte] Enviar Mensagem Ticket',
  props<{ id: string; corpo: string }>()
);

export const suporteOperacaoSucesso = createAction(
  '[Suporte] Operacao Sucesso',
  props<{ mensagem: string }>()
);

export const suporteOperacaoFalhou = createAction(
  '[Suporte API] Operação Falhou',
  props<{ erro: string }>()
);
