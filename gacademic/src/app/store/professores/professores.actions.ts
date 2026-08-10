import { createAction, props } from '@ngrx/store';
import { Professor } from './professores.models';

export const carregarProfessores = createAction('[Professores] Carregar Professores');
export const carregarProfessoresSucesso = createAction(
  '[Professores] Carregar Professores Sucesso',
  props<{ professores: Professor[] }>()
);
export const criarProfessor = createAction(
  '[Professores] Criar Professor',
  props<{ nome_completo: string, email: string, palavra_passe: string, formacao_academica: string | null }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const professoresOperacaoFalhou = createAction(
  '[Professores API] Operação Falhou',
  props<{ erro: string }>()
);
