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

// Layout HTML próprio da escola para um tipo de documento — ver
// app/database/models_documentos.py::TemplateDocumentoPersonalizado.
export interface TemplateDocumento {
  tipo_documento: TipoDocumento;
  nome: string;
  personalizado: boolean;
  corpo_html: string | null;
  atualizado_em: string | null;
}

// Variáveis Jinja2 disponíveis em cada tipo de documento — ver
// _CONTEXTOS_AMOSTRA em app/cruds/documentos.py (têm de espelhar
// exatamente isto, incluindo a forma dos objetos em listas).
export const VARIAVEIS_TEMPLATE: Record<TipoDocumento, string[]> = {
  CERTIFICADO: ['aluno_nome', 'numero_documento', 'turma_nome', 'ano_letivo'],
  DECLARACAO: ['aluno_nome', 'numero_documento', 'turma_nome', 'ano_letivo'],
  BOLETIM: ['aluno_nome', 'turma_nome', 'ano_letivo', 'notas (lista: disciplina, periodo, tipo, valor)'],
  HISTORICO_ESCOLAR: ['aluno_nome', 'numero_documento', 'data_nascimento', 'anos (lista: ano_letivo, turma_nome, status_matricula, notas)'],
  OUTRO: ['aluno_nome', 'descricao'],
};
