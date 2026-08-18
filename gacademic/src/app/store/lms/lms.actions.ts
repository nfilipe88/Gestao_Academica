import { createAction, props } from '@ngrx/store';
import { LmsExame, LmsExameDetalhe, LmsQuestao, LmsResultadoAlunoExame, MaterialAula, TipoQuestaoLms } from './lms.models';

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

// ==========================================
// BANCO DE QUESTÕES
// ==========================================
export const carregarBancoQuestoes = createAction(
  '[Lms] Carregar Banco Questoes',
  props<{ disciplina_id: string }>()
);
export const carregarBancoQuestoesSucesso = createAction(
  '[Lms] Carregar Banco Questoes Sucesso',
  props<{ questoes: LmsQuestao[] }>()
);

export const criarQuestao = createAction(
  '[Lms] Criar Questao',
  props<{
    disciplina_id: string, enunciado: string, tipo: TipoQuestaoLms,
    opcoes: string[], resposta_correta: string, valor: number
  }>()
);

export const atualizarQuestao = createAction(
  '[Lms] Atualizar Questao',
  props<{
    questao_id: string, disciplina_id: string, enunciado: string, tipo: TipoQuestaoLms,
    opcoes: string[], resposta_correta: string, valor: number
  }>()
);

export const apagarQuestao = createAction(
  '[Lms] Apagar Questao',
  props<{ questao_id: string, disciplina_id: string }>()
);

// ==========================================
// EXAMES (motor online) — gestão pelo professor/staff
// ==========================================
export const carregarExames = createAction(
  '[Lms] Carregar Exames',
  props<{ alocacao_id: string }>()
);
export const carregarExamesSucesso = createAction(
  '[Lms] Carregar Exames Sucesso',
  props<{ exames: LmsExame[] }>()
);

export const criarExame = createAction(
  '[Lms] Criar Exame',
  props<{
    alocacao_id: string, titulo: string, data_inicio: string, data_fim: string,
    duracao_minutos: number, baralhar_perguntas: boolean, questao_ids: string[]
  }>()
);

export const publicarExame = createAction('[Lms] Publicar Exame', props<{ exame_id: string, alocacao_id: string }>());
export const despublicarExame = createAction('[Lms] Despublicar Exame', props<{ exame_id: string, alocacao_id: string }>());
export const apagarExame = createAction('[Lms] Apagar Exame', props<{ exame_id: string, alocacao_id: string }>());

export const carregarExameDetalhe = createAction('[Lms] Carregar Exame Detalhe', props<{ exame_id: string }>());
export const carregarExameDetalheSucesso = createAction(
  '[Lms] Carregar Exame Detalhe Sucesso',
  props<{ exame: LmsExameDetalhe }>()
);
export const limparExameDetalhe = createAction('[Lms] Limpar Exame Detalhe');

export const carregarResultadosExame = createAction('[Lms] Carregar Resultados Exame', props<{ exame_id: string }>());
export const carregarResultadosExameSucesso = createAction(
  '[Lms] Carregar Resultados Exame Sucesso',
  props<{ exame_id: string, resultados: LmsResultadoAlunoExame[] }>()
);
