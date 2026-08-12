// Alinhado com app/api/v1/financeiro.py.

export interface MatriculaResumo {
  matricula_id: string;
  turma_id: string;
  nome_turma: string;
  status_matricula: string;
  ano_letivo: number;
  data_matricula: string;
}

export interface ResponsavelElegivel {
  responsavel_id: string;
  nome_completo: string;
  email: string | null;
  tipo_parentesco: string;
  responsavel_financeiro: boolean;
}

export interface ContratoFinanceiro {
  id: string;
  tenant_id: string;
  matricula_id: string;
  responsavel_id: string;
  valor_total_anual: number;
  quantidade_parcelas: number;
  dia_vencimento_padrao: number;
  percentual_desconto_bolsa: number;
  data_criacao: string;
}

// PENDENTE/PAGO/CANCELADO/NEGOCIADO vêm da base de dados; ATRASADO é
// sempre calculado on-the-fly pelo back-end (RN02) — nunca gravado.
export type StatusFatura = 'PENDENTE' | 'PAGO' | 'ATRASADO' | 'CANCELADO' | 'NEGOCIADO';

export interface TransacaoAtiva {
  transacao_id: string;
  metodo: string; // 'PAYPAL' por agora
  order_id: string;
  approve_url: string | null;
}

export interface FaturaMensalidade {
  id: string;
  contrato_id: string;
  numero_parcela: number;
  valor_original: number;
  data_vencimento: string;
  status_pagamento: StatusFatura;
  status_efetivo: StatusFatura;
  valor_atualizado: number;
  juros_aplicados: number;
  multa_aplicada: number;
  dias_atraso: number;
  data_pagamento_realizado: string | null;
  valor_pago_realizado: number | null;
  forma_pagamento: string | null;
  transacoes_ativas: TransacaoAtiva[];
}

export interface CobrancaGerada {
  transacao_id: string;
  fatura_id: string;
  valor_cobrado: number;
  dados_pagamento: { approve_url: string | null };
  status: string;
}
