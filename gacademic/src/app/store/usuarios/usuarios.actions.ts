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

// Para quem perdeu o acesso ao e-mail e não consegue receber o código do
// login — nunca a própria conta (essa é no Perfil, pede a palavra-passe).
export const desativarDoisFatores = createAction(
  '[Usuarios] Desativar Dois Fatores',
  props<{ tenant_id?: string, usuario_id: string }>()
);

// Perfil da escola (ex.: "Tesouraria"); null = volta ao perfil base. Só a
// própria escola do Gestor (os perfis da escola são dela).
export const atribuirPerfilPersonalizado = createAction(
  '[Usuarios] Atribuir Perfil Personalizado',
  props<{ usuario_id: string, perfil_personalizado_id: string | null }>()
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
