import { createAction, props } from '@ngrx/store';
import { OperacoesCrud, PermissaoModulo } from './permissoes.models';

export const carregarPermissoes = createAction('[Permissoes] Carregar Permissoes');
export const carregarPermissoesSucesso = createAction(
  '[Permissoes] Carregar Permissoes Sucesso',
  props<{ permissoes: PermissaoModulo[] }>()
);

// Disparado pela combobox de operações CRUD de cada célula — sem botão
// "Guardar" à parte: ao selecionar, atualiza logo (ver
// permissoes.component.ts::onAlterarOperacoes).
// escola = true: restrição da própria escola (Gestor, PUT .../escola);
// false: mapa base de todas as escolas (Super Admin, PATCH).
export const atualizarPermissao = createAction(
  '[Permissoes] Atualizar Permissao',
  props<{ id: string; operacoes: OperacoesCrud; escola: boolean }>()
);
export const atualizarPermissaoSucesso = createAction(
  '[Permissoes] Atualizar Permissao Sucesso',
  props<{ permissao: PermissaoModulo }>()
);

export const permissoesOperacaoFalhou = createAction(
  '[Permissoes API] Operação Falhou',
  props<{ erro: string }>()
);
