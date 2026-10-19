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
  // Teto do código: o que as rotas deste módulo deixam este perfil fazer —
  // o mapa só restringe, nunca dá acima disto.
  codigo_pode_criar: boolean;
  codigo_pode_ler: boolean;
  codigo_pode_atualizar: boolean;
  codigo_pode_apagar: boolean;
  // Linha sem rotas associadas (ex.: Visão Geral) — só descreve.
  informativo: boolean;
  // Operações que nunca se podem tirar (o Gestor nas Configurações).
  protegidas: (keyof OperacoesCrud)[];
  // Só na vista do Gestor: o que vale na escola dele.
  escola_pode_criar?: boolean | null;
  escola_pode_ler?: boolean | null;
  escola_pode_atualizar?: boolean | null;
  escola_pode_apagar?: boolean | null;
}

// Corpo do PATCH — as 4 flags que a combobox de operações CRUD produz.
export interface OperacoesCrud {
  pode_criar: boolean;
  pode_ler: boolean;
  pode_atualizar: boolean;
  pode_apagar: boolean;
}
