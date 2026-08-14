// Alinhado com app/api/v1/admin.py.

export type StatusTenant = 'ATIVO' | 'SUSPENSO';

export interface TenantResumo {
  id: string;
  nome_fantasia: string;
  razao_social: string | null;
  nif: string;
  status: StatusTenant;
  data_criacao: string;
  total_usuarios: number;
  total_alunos: number;
  total_professores: number;
}
