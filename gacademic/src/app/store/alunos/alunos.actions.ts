import { createAction, props } from '@ngrx/store';
import { Aluno, AlunoResponsavelVinculo, Responsavel } from './alunos.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

// --- Alunos ---
// page/page_size opcionais: quem só quer "a lista para um <select>"
// (ex.: Documentos, Transferências) chama sem argumentos e o effect usa
// os valores por omissão; a página de Alunos (tabela) passa-os
// explicitamente conforme o utilizador pagina.
export const carregarAlunos = createAction(
  '[Alunos] Carregar Alunos',
  props<{
    page?: number, page_size?: number, busca?: string,
    data_nascimento_inicio?: string, data_nascimento_fim?: string
  }>()
);
export const carregarAlunosSucesso = createAction(
  '[Alunos] Carregar Alunos Sucesso',
  props<{ alunos: Aluno[], paginacao: EstadoPaginacao }>()
);
export const criarAluno = createAction(
  '[Alunos] Criar Aluno',
  props<{ matricula_interna: string, nome_completo: string, data_nascimento: string, numero_documento: string | null }>()
);

// --- Responsáveis ---
export const carregarResponsaveis = createAction(
  '[Alunos] Carregar Responsaveis',
  props<{ page?: number, page_size?: number }>()
);
export const carregarResponsaveisSucesso = createAction(
  '[Alunos] Carregar Responsaveis Sucesso',
  props<{ responsaveis: Responsavel[], paginacao: EstadoPaginacao }>()
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

// --- Acesso ao Portal (login próprio para Aluno/Responsável) ---
export const criarAcessoAluno = createAction(
  '[Alunos] Criar Acesso Aluno',
  props<{ aluno_id: string, email: string, palavra_passe: string }>()
);
export const criarAcessoResponsavel = createAction(
  '[Alunos] Criar Acesso Responsavel',
  props<{ responsavel_id: string, email: string, palavra_passe: string }>()
);
export const alunosOperacaoSucesso = createAction(
  '[Alunos] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão do módulo académico): sem isto, um
// erro HTTP dentro de um effect fica por apanhar e mata esse effect para
// o resto da sessão.
export const alunosOperacaoFalhou = createAction(
  '[Alunos API] Operação Falhou',
  props<{ erro: string }>()
);
