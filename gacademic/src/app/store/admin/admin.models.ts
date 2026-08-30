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
// Mesma lista de app/core/modulos.py::MODULOS_GATEAVEIS — um módulo
// AUSENTE dos módulos de um plano fica mesmo bloqueado (403) para as
// escolas desse plano, não é só uma questão de preço. Os módulos
// fundamentais (Alunos, Turmas, Cursos, Configurações, ...) nunca
// aparecem aqui porque nunca dependem do plano.
export const MODULOS_GATEAVEIS = [
  'CRM', 'Financeiro', 'Indicadores', 'Comunicações', 'Horários',
  'Diário de Classe', 'Trabalhos / Tarefas', 'Transferências de Alunos', 'Professores',
] as const;

export interface PlanoSaaSModulo {
  modulo: string;
  preco_adicional: number;
}

export interface PlanoSaaS {
  id: string;
  nome: string;
  // Substitui a antiga mensalidade fixa — a fatura da escola passa a
  // ser preco_por_aluno × nº de alunos cadastrados, mais o que os
  // módulos incluídos (abaixo) custarem à parte.
  preco_por_aluno: number;
  limite_alunos: number | null;
  descricao: string | null;
  // Dias de acesso grátis ao atribuir este plano a uma escola nova (0 =
  // sem período de teste, cobrança normal desde o início).
  dias_periodo_teste: number;
  ativo: boolean;
  modulos: PlanoSaaSModulo[];
}

export interface AssinaturaTenant {
  id: string;
  plano_id: string;
  nome_plano: string;
  preco_por_aluno: number;
  total_alunos: number;
  mensalidade: number;
  modulos: PlanoSaaSModulo[];
  data_inicio: string;
  proxima_cobranca: string;
  status: 'ATIVA' | 'CANCELADA';
  em_periodo_teste: boolean;
}

export interface ResumoMrrPorPlano {
  nome_plano: string;
  total_assinaturas: number;
  receita_mensal: number;
}

export interface ResumoMrr {
  mrr: number;
  total_assinaturas_ativas: number;
  por_plano: ResumoMrrPorPlano[];
}

// ==========================================
// TICKETS DE SUPORTE — cross-tenant
// ==========================================
export type EstadoTicket = 'ABERTO' | 'EM_ANDAMENTO' | 'RESOLVIDO' | 'FECHADO';

export interface TicketAdminRegisto {
  id: string;
  tenant_id: string | null;
  nome_escola: string | null; // null = visitante do site público, sem conta
  autor_nome: string;
  autor_email: string;
  assunto: string;
  estado: EstadoTicket;
  criado_em: string;
  atualizado_em: string;
}

export interface TicketMensagemRegisto {
  id: string;
  autor_tipo: 'CLIENTE' | 'SUPORTE';
  autor_nome: string;
  corpo: string;
  criado_em: string;
}

export interface TicketAdminComMensagens extends TicketAdminRegisto {
  mensagens: TicketMensagemRegisto[];
}
