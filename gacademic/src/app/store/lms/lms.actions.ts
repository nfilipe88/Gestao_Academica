import { createAction, props } from '@ngrx/store';
import { MaterialAula } from './lms.models';

export const carregarMateriais = createAction(
  '[Lms] Carregar Materiais',
  props<{ turma_id: string, disciplina_id: string }>()
);
export const carregarMateriaisSucesso = createAction(
  '[Lms] Carregar Materiais Sucesso',
  props<{ materiais: MaterialAula[] }>()
);

export const criarMaterial = createAction(
  '[Lms] Criar Material',
  props<{
    turma_id: string, disciplina_id: string, titulo: string, corpo: string,
    objetivo_aprendizagem_id: string | null, publicado: boolean
  }>()
);

export const atualizarMaterial = createAction(
  '[Lms] Atualizar Material',
  props<{
    material_id: string, turma_id: string, disciplina_id: string, titulo: string, corpo: string,
    objetivo_aprendizagem_id: string | null, publicado: boolean
  }>()
);

export const apagarMaterial = createAction(
  '[Lms] Apagar Material',
  props<{ material_id: string, turma_id: string, disciplina_id: string }>()
);

export const sugerirConteudo = createAction(
  '[Lms] Sugerir Conteudo',
  props<{
    turma_id: string, disciplina_id: string, titulo: string,
    objetivo_aprendizagem_id: string | null, instrucoes: string | null
  }>()
);
export const sugerirConteudoSucesso = createAction(
  '[Lms] Sugerir Conteudo Sucesso',
  props<{ sugestao: string }>()
);
export const limparSugestaoConteudo = createAction('[Lms] Limpar Sugestao Conteudo');

export const lmsOperacaoSucesso = createAction(
  '[Lms] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha: sem isto, um erro HTTP dentro de um effect
// fica por apanhar e mata esse effect para o resto da sessão.
export const lmsOperacaoFalhou = createAction(
  '[Lms API] Operação Falhou',
  props<{ erro: string }>()
);
