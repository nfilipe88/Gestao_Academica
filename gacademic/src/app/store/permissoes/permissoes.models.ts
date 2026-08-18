// Alinhado com app/schemas/permissoes.py — uma célula do Mapa de
// Permissões (módulo x perfil), com as 4 operações CRUD em separado.
export type PerfilPermissao = 'super_admin' | 'gestor' | 'secretaria' | 'professor' | 'aluno_responsavel';

export interface PermissaoModulo {
  id: string;
  ordem: number;
  modulo: string;
  perfil: PerfilPermissao;
  pode_criar: boolean;
  pode_ler: boolean;
  pode_atualizar: boolean;
  pode_apagar: boolean;
}

// Corpo do PATCH — as 4 flags que a combobox de operações CRUD produz.
export interface OperacoesCrud {
  pode_criar: boolean;
  pode_ler: boolean;
  pode_atualizar: boolean;
  pode_apagar: boolean;
}
