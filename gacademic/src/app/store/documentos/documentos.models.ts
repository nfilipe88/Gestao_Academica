// Alinhado com app/api/v1/documentos.py.

export type TipoDocumento = 'CERTIFICADO' | 'DECLARACAO' | 'HISTORICO_ESCOLAR' | 'BOLETIM' | 'OUTRO';
export type FormatoEntrega = 'DIGITAL' | 'FISICA';
export type StatusSolicitacaoEmissao = 'PENDENTE_PAGAMENTO' | 'PAGO' | 'ENTREGUE' | 'CANCELADO';
export type StatusSolicitacaoEscola = 'PENDENTE' | 'RESPONDIDO' | 'CONCLUIDO';
export type DestinatarioEscola = 'ALUNO' | 'RESPONSAVEL' | 'PROFESSOR';

export interface PrecoDocumento {
  tipo_documento: TipoDocumento;
  nome: string;
  preco: number;
  ativo: boolean;
}

export interface SolicitacaoDocumentoEmissao {
  id: string;
  aluno_id: string;
  aluno_nome: string | null;
  tipo_documento: TipoDocumento;
  nome_tipo_documento: string;
  descricao_outro: string | null;
  formato_entrega: FormatoEntrega;
  preco: number;
  status: StatusSolicitacaoEmissao;
  observacoes_escola: string | null;
  data_solicitacao: string;
  data_pagamento: string | null;
  data_conclusao: string | null;
}

export interface CobrancaDocumentoGerada {
  solicitacao_id: string;
  valor_cobrado: number;
  dados_pagamento: { approve_url: string | null };
}

export interface SolicitacaoDocumentoEscola {
  id: string;
  destinatario_tipo: DestinatarioEscola;
  destinatario_nome: string | null;
  destinatario_aluno_id: string | null;
  destinatario_responsavel_id: string | null;
  destinatario_professor_id: string | null;
  solicitante_nome: string | null;
  titulo: string;
  descricao: string;
  status: StatusSolicitacaoEscola;
  resposta_texto: string | null;
  respondido_em: string | null;
  data_solicitacao: string;
}
