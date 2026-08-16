import { createAction, props } from '@ngrx/store';
import { Alocacao, Professor } from './professores.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

export const carregarProfessores = createAction(
  '[Professores] Carregar Professores',
  props<{ page?: number, page_size?: number, busca?: string }>()
);
export const carregarProfessoresSucesso = createAction(
  '[Professores] Carregar Professores Sucesso',
  props<{ professores: Professor[], paginacao: EstadoPaginacao }>()
);
export const criarProfessor = createAction(
  '[Professores] Criar Professor',
  props<{ nome_completo: string, email: string, palavra_passe: string, formacao_academica: string | null }>()
);

// Alocação: qual professor lecciona qual disciplina em qual turma.
export const carregarAlocacoes = createAction('[Professores] Carregar Alocacoes');
export const carregarAlocacoesSucesso = createAction(
  '[Professores] Carregar Alocacoes Sucesso',
  props<{ alocacoes: Alocacao[] }>()
);
export const criarAlocacao = createAction(
  '[Professores] Criar Alocacao',
  props<{ professor_id: string, turma_id: string, disciplina_id: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const professoresOperacaoFalhou = createAction(
  '[Professores API] Operação Falhou',
  props<{ erro: string }>()
);
