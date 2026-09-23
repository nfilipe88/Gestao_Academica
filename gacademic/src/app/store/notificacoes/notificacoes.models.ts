// Alinhado com app/api/v1/notificacoes.py.

export type TipoNotificacao =
  | 'COMUNICADO' | 'COMUNICADO_RESPOSTA' | 'SOLICITACAO_DOCUMENTO' | 'SOLICITACAO_TRANSFERENCIA'
  | 'LICENCA' | 'SISTEMA' | 'EXAME_CORRIGIDO' | 'TAREFA_AVALIADA' | 'REMATRICULA' | 'PROPINA';

export interface Notificacao {
  id: string;
  tipo: TipoNotificacao;
  titulo: string;
  mensagem: string;
  link: string | null;
  lida: boolean;
  data_criacao: string;
}
