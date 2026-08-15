// Alinhado com app/api/v1/transferencias.py.

export type StatusTransferencia = 'PENDENTE' | 'REJEITADA' | 'CONCLUIDA';

export interface SolicitacaoTransferencia {
  id: string;
  tenant_id: string;
  nome_instituicao_origem: string | null;
  aluno_id: string;
  aluno_nome: string | null;
  tenant_destino_id: string;
  nome_instituicao_destino: string | null;
  nif_destino: string;
  motivo: string | null;
  status: StatusTransferencia;
  observacoes_decisao: string | null;
  aluno_novo_id: string | null;
  data_solicitacao: string;
  data_decisao: string | null;
}
