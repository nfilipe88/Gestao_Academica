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
  nome_plano: string | null;
  em_periodo_teste: boolean;
}

// Filtros da listagem de Instituições — nome (ILIKE), plano_id
// (só escolas com assinatura ATIVA nesse plano) e intervalo de nº de
// utilizadores. Tudo opcional; omitido = sem esse filtro.
export interface FiltrosTenants {
  nome?: string;
  plano_id?: string;
  usuarios_min?: number | null;
  usuarios_max?: number | null;
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
  // Dias de acesso grátis ao atribuir este plano a uma escola nova (0 =
  // sem período de teste, cobrança normal desde o início).
  dias_periodo_teste: number;
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
  em_periodo_teste: boolean;
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
