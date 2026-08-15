// Alinhado com app/api/v1/notificacoes.py.

export type TipoNotificacao = 'COMUNICADO' | 'SOLICITACAO_DOCUMENTO' | 'SOLICITACAO_TRANSFERENCIA' | 'LICENCA' | 'SISTEMA';

export interface Notificacao {
  id: string;
  tipo: TipoNotificacao;
  titulo: string;
  mensagem: string;
  link: string | null;
  lida: boolean;
  data_criacao: string;
}
