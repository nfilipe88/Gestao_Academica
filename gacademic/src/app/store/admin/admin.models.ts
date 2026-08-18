// Alinhado com app/api/v1/admin.py.

export type StatusTenant = 'ATIVO' | 'SUSPENSO';

export interface TenantResumo {
  id: string;
  nome_fantasia: string;
  razao_social: string | null;
  nif: string;
  status: StatusTenant;
  data_validade_licenca: string | null; // YYYY-MM-DD
  data_criacao: string;
  total_usuarios: number;
  total_alunos: number;
  total_professores: number;
}

// ==========================================
// SAAS BILLING — Planos, Assinaturas e MRR
// ==========================================
export interface PlanoSaaS {
  id: string;
  nome: string;
  preco_mensal: number;
  limite_alunos: number | null;
  descricao: string | null;
  ativo: boolean;
}

export interface AssinaturaTenant {
  id: string;
  plano_id: string;
  nome_plano: string;
  preco_mensal: number;
  data_inicio: string;
  proxima_cobranca: string;
  status: 'ATIVA' | 'CANCELADA';
}

export interface ResumoMrrPorPlano {
  nome_plano: string;
  preco_mensal: number;
  total_assinaturas: number;
  receita_mensal: number;
}

export interface ResumoMrr {
  mrr: number;
  total_assinaturas_ativas: number;
  por_plano: ResumoMrrPorPlano[];
}
