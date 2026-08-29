import { createAction, props } from '@ngrx/store';
import { AssinaturaTenant, FiltrosTenants, PlanoSaaS, PlanoSaaSModulo, ResumoMrr, StatusTenant, TenantResumo } from './admin.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

export const carregarTenants = createAction(
  '[Admin] Carregar Tenants',
  props<{ page?: number, page_size?: number, filtros?: FiltrosTenants }>()
);

// Onboarding gatekeeping pelo Super Admin — em alternativa ao
// auto-serviço em /registo (ver api/v1/admin.py::criar_tenant).
export const criarTenant = createAction(
  '[Admin] Criar Tenant',
  props<{ nome_fantasia: string; nif: string; nome_gestor: string; email_gestor: string; palavra_passe: string }>()
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

// ==========================================
// SAAS BILLING — Planos, Assinaturas e MRR
// ==========================================

export const carregarPlanos = createAction('[Admin] Carregar Planos');
export const carregarPlanosSucesso = createAction(
  '[Admin] Carregar Planos Sucesso',
  props<{ planos: PlanoSaaS[] }>()
);

export const criarPlano = createAction(
  '[Admin] Criar Plano',
  props<{
    nome: string; preco_por_aluno: number; limite_alunos: number | null; descricao: string | null;
    dias_periodo_teste: number; modulos: PlanoSaaSModulo[];
  }>()
);

export const atualizarPlano = createAction(
  '[Admin] Atualizar Plano',
  props<{
    id: string; nome: string; preco_por_aluno: number; limite_alunos: number | null; descricao: string | null;
    dias_periodo_teste: number; ativo: boolean; modulos: PlanoSaaSModulo[];
  }>()
);

export const apagarPlano = createAction('[Admin] Apagar Plano', props<{ id: string }>());

export const carregarMrr = createAction('[Admin] Carregar MRR');
export const carregarMrrSucesso = createAction(
  '[Admin] Carregar MRR Sucesso',
  props<{ mrr: ResumoMrr }>()
);

export const carregarAssinaturaTenant = createAction(
  '[Admin] Carregar Assinatura Tenant',
  props<{ tenant_id: string }>()
);
export const carregarAssinaturaTenantSucesso = createAction(
  '[Admin] Carregar Assinatura Tenant Sucesso',
  props<{ tenant_id: string; assinatura: AssinaturaTenant | null }>()
);

export const definirAssinaturaTenant = createAction(
  '[Admin] Definir Assinatura Tenant',
  props<{ tenant_id: string; plano_id: string; proxima_cobranca: string }>()
);

export const cancelarAssinaturaTenant = createAction(
  '[Admin] Cancelar Assinatura Tenant',
  props<{ tenant_id: string }>()
);
