import { createAction, props } from '@ngrx/store';
import { AuditLogRegisto, FiltrosAuditoria } from './auditoria.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

// tenant_id opcional em todas as ações: omitido = a própria escola do
// Gestor (usa /api/v1/auditoria); presente = qualquer escola, só o
// Super Admin (usa /api/v1/admin/tenants/{tenant_id}/auditoria) — ver
// auditoria.effects.ts::baseUrl.

export const carregarAuditoria = createAction(
  '[Auditoria] Carregar Auditoria',
  props<{ tenant_id?: string; page?: number; page_size?: number; filtros?: FiltrosAuditoria }>()
);
export const carregarAuditoriaSucesso = createAction(
  '[Auditoria] Carregar Auditoria Sucesso',
  props<{ registos: AuditLogRegisto[]; paginacao: EstadoPaginacao }>()
);

export const carregarEntidades = createAction(
  '[Auditoria] Carregar Entidades',
  props<{ tenant_id?: string }>()
);
export const carregarEntidadesSucesso = createAction(
  '[Auditoria] Carregar Entidades Sucesso',
  props<{ entidades: string[] }>()
);

export const auditoriaOperacaoFalhou = createAction(
  '[Auditoria API] Operação Falhou',
  props<{ erro: string }>()
);
