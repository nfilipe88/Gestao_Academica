// Alinhado com app/schemas/suporte.py.

export type EstadoTicket = 'ABERTO' | 'EM_ANDAMENTO' | 'RESOLVIDO' | 'FECHADO';

export interface TicketRegisto {
  id: string;
  autor_nome: string;
  autor_email: string;
  assunto: string;
  estado: EstadoTicket;
  criado_em: string;
  atualizado_em: string;
}

export interface TicketAdminRegisto extends TicketRegisto {
  tenant_id: string | null;
  nome_escola: string | null;
}

export interface TicketMensagemRegisto {
  id: string;
  autor_tipo: 'CLIENTE' | 'SUPORTE';
  autor_nome: string;
  corpo: string;
  criado_em: string;
}

export interface TicketComMensagens extends TicketRegisto {
  mensagens: TicketMensagemRegisto[];
}

export interface TicketAdminComMensagens extends TicketAdminRegisto {
  mensagens: TicketMensagemRegisto[];
}
