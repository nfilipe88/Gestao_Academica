import { createAction, props } from '@ngrx/store';
import { StatusTenant, TenantResumo } from './admin.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

export const carregarTenants = createAction(
  '[Admin] Carregar Tenants',
  props<{ page?: number, page_size?: number }>()
);
export const carregarTenantsSucesso = createAction(
  '[Admin] Carregar Tenants Sucesso',
  props<{ tenants: TenantResumo[], paginacao: EstadoPaginacao }>()
);

export const atualizarStatusTenant = createAction(
  '[Admin] Atualizar Status Tenant',
  props<{ tenant_id: string, status: StatusTenant }>()
);

export const atualizarValidadeLicenca = createAction(
  '[Admin] Atualizar Validade Licenca',
  props<{ tenant_id: string, data_validade_licenca: string | null }>()
);

// Disparo manual do job diário — o scheduler já corre isto sozinho
// todos os dias às 07:00; isto é só para testar/forçar já.
export const processarValidadeLicencas = createAction('[Admin] Processar Validade Licencas');

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
