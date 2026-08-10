import { createAction, props } from '@ngrx/store';
import { Aluno, AlunoResponsavelVinculo, Responsavel } from './alunos.models';

// --- Alunos ---
export const carregarAlunos = createAction('[Alunos] Carregar Alunos');
export const carregarAlunosSucesso = createAction(
  '[Alunos] Carregar Alunos Sucesso',
  props<{ alunos: Aluno[] }>()
);
export const criarAluno = createAction(
  '[Alunos] Criar Aluno',
  props<{ matricula_interna: string, nome_completo: string, data_nascimento: string, numero_documento: string | null }>()
);

// --- Responsáveis ---
export const carregarResponsaveis = createAction('[Alunos] Carregar Responsaveis');
export const carregarResponsaveisSucesso = createAction(
  '[Alunos] Carregar Responsaveis Sucesso',
  props<{ responsaveis: Responsavel[] }>()
);
export const criarResponsavel = createAction(
  '[Alunos] Criar Responsavel',
  props<{ nome_completo: string, telefone_contato: string, numero_documento: string | null, email: string | null }>()
);

// --- Vínculo Aluno <-> Responsável ---
export const carregarResponsaveisDoAluno = createAction(
  '[Alunos] Carregar Responsaveis Do Aluno',
  props<{ aluno_id: string }>()
);
export const carregarResponsaveisDoAlunoSucesso = createAction(
  '[Alunos] Carregar Responsaveis Do Aluno Sucesso',
  props<{ aluno_id: string, vinculos: AlunoResponsavelVinculo[] }>()
);
export const vincularResponsavel = createAction(
  '[Alunos] Vincular Responsavel',
  props<{ aluno_id: string, responsavel_id: string, tipo_parentesco: string, responsavel_financeiro: boolean }>()
);

// Ação genérica de falha (mesmo padrão do módulo académico): sem isto, um
// erro HTTP dentro de um effect fica por apanhar e mata esse effect para
// o resto da sessão.
export const alunosOperacaoFalhou = createAction(
  '[Alunos API] Operação Falhou',
  props<{ erro: string }>()
);
