import { createAction, props } from '@ngrx/store';
import { StatusTenant, TenantResumo } from './admin.models';

export const carregarTenants = createAction('[Admin] Carregar Tenants');
export const carregarTenantsSucesso = createAction(
  '[Admin] Carregar Tenants Sucesso',
  props<{ tenants: TenantResumo[] }>()
);

export const atualizarStatusTenant = createAction(
  '[Admin] Atualizar Status Tenant',
  props<{ tenant_id: string, status: StatusTenant }>()
);

export const adminOperacaoSucesso = createAction(
  '[Admin] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const adminOperacaoFalhou = createAction(
  '[Admin API] Operação Falhou',
  props<{ erro: string }>()
);
