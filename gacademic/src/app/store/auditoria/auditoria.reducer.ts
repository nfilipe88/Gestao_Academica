import { createReducer, on } from '@ngrx/store';
import * as AuditoriaActions from './auditoria.actions';
import { AuditLogRegisto } from './auditoria.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface AuditoriaState {
  registos: AuditLogRegisto[];
  paginacao: EstadoPaginacao;
  entidades: string[];
  erro: string | null;
}

export const initialState: AuditoriaState = {
  registos: [],
  paginacao: PAGINACAO_INICIAL,
  entidades: [],
  erro: null,
};

export const auditoriaReducer = createReducer(
  initialState,
  on(AuditoriaActions.carregarAuditoria, (state) => ({ ...state, erro: null })),
  on(AuditoriaActions.carregarAuditoriaSucesso, (state, { registos, paginacao }) => ({ ...state, registos, paginacao })),
  on(AuditoriaActions.carregarEntidadesSucesso, (state, { entidades }) => ({ ...state, entidades })),
  on(AuditoriaActions.auditoriaOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
