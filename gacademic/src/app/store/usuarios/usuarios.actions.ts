import { createAction, props } from '@ngrx/store';
import { UsuarioAuditoriaRegisto, UsuarioStaff } from './usuarios.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

// tenant_id é opcional em todas as ações: omitido = a própria escola
// do Gestor (usa /api/v1/usuarios); presente = qualquer escola, usado
// pelo Super Admin (usa /api/v1/admin/tenants/{tenant_id}/usuarios) —
// ver usuarios.effects.ts::baseUrl. Mesma store, dois consumidores.

export const carregarUsuarios = createAction(
  '[Usuarios] Carregar Usuarios',
  props<{ tenant_id?: string, page?: number, page_size?: number }>()
);
export const carregarUsuariosSucesso = createAction(
  '[Usuarios] Carregar Usuarios Sucesso',
  props<{ usuarios: UsuarioStaff[], paginacao: EstadoPaginacao }>()
);

export const criarSecretaria = createAction(
  '[Usuarios] Criar Secretaria',
  props<{ tenant_id?: string, nome_completo: string, email: string, palavra_passe: string }>()
);

export const alterarPerfil = createAction(
  '[Usuarios] Alterar Perfil',
  props<{ tenant_id?: string, usuario_id: string, perfil_acesso: 'GESTOR' | 'SECRETARIA' }>()
);

export const alterarAtivo = createAction(
  '[Usuarios] Alterar Ativo',
  props<{ tenant_id?: string, usuario_id: string, ativo: boolean }>()
);

export const carregarAuditoria = createAction(
  '[Usuarios] Carregar Auditoria',
  props<{ tenant_id?: string, page?: number, page_size?: number }>()
);
export const carregarAuditoriaSucesso = createAction(
  '[Usuarios] Carregar Auditoria Sucesso',
  props<{ auditoria: UsuarioAuditoriaRegisto[], paginacao: EstadoPaginacao }>()
);

export const usuariosOperacaoSucesso = createAction(
  '[Usuarios] Operacao Sucesso',
  props<{ mensagem: string }>()
);

export const usuariosOperacaoFalhou = createAction(
  '[Usuarios API] Operação Falhou',
  props<{ erro: string }>()
);
