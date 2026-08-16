import { createReducer, on } from '@ngrx/store';
import * as UsuariosActions from './usuarios.actions';
import { UsuarioAuditoriaRegisto, UsuarioStaff } from './usuarios.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface UsuariosState {
  usuarios: UsuarioStaff[];
  paginacaoUsuarios: EstadoPaginacao;
  auditoria: UsuarioAuditoriaRegisto[];
  paginacaoAuditoria: EstadoPaginacao;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: UsuariosState = {
  usuarios: [],
  paginacaoUsuarios: PAGINACAO_INICIAL,
  auditoria: [],
  paginacaoAuditoria: PAGINACAO_INICIAL,
  mensagem: null,
  erro: null,
};

export const usuariosReducer = createReducer(
  initialState,
  on(UsuariosActions.carregarUsuarios, UsuariosActions.criarSecretaria,
     UsuariosActions.alterarPerfil, UsuariosActions.alterarAtivo, UsuariosActions.carregarAuditoria,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(UsuariosActions.carregarUsuariosSucesso, (state, { usuarios, paginacao }) => ({ ...state, usuarios, paginacaoUsuarios: paginacao })),
  on(UsuariosActions.carregarAuditoriaSucesso, (state, { auditoria, paginacao }) => ({ ...state, auditoria, paginacaoAuditoria: paginacao })),
  on(UsuariosActions.usuariosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(UsuariosActions.usuariosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
