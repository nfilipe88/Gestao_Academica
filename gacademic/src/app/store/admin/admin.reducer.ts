import { createReducer, on } from '@ngrx/store';
import * as AdminActions from './admin.actions';
import { TenantResumo } from './admin.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface AdminState {
  tenants: TenantResumo[];
  paginacaoTenants: EstadoPaginacao;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: AdminState = {
  tenants: [],
  paginacaoTenants: PAGINACAO_INICIAL,
  mensagem: null,
  erro: null
};

export const adminReducer = createReducer(
  initialState,
  on(AdminActions.carregarTenants, AdminActions.atualizarStatusTenant,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(AdminActions.carregarTenantsSucesso, (state, { tenants, paginacao }) => ({ ...state, tenants, paginacaoTenants: paginacao })),
  on(AdminActions.adminOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(AdminActions.adminOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
