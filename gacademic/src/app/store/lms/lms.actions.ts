import { createAction, props } from '@ngrx/store';
import {
  LmsAtribuicaoVariante, LmsCorrecaoQuestaoInput, LmsExameDetalhe, LmsGrupoExame, LmsQuestao, LmsResultadoAlunoExame,
  Modalidade, MaterialAula, TipoQuestaoLms
} from './lms.models';

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
// EXAMES (motor online) — gestão pelo professor/staff. Um GRUPO tem
// 1+ variantes; só Gestor/Secretaria pode iniciarGrupoExame/reatribuirVariante.
// ==========================================
export const carregarGruposExame = createAction(
  '[Lms] Carregar Grupos Exame',
  props<{ alocacao_id: string }>()
);
export const carregarGruposExameSucesso = createAction(
  '[Lms] Carregar Grupos Exame Sucesso',
  props<{ grupos: LmsGrupoExame[] }>()
);

export const criarGrupoExame = createAction(
  '[Lms] Criar Grupo Exame',
  props<{
    alocacao_id: string, titulo: string, data_inicio: string, data_fim: string,
    duracao_minutos: number, baralhar_perguntas: boolean, modalidade: Modalidade,
    periodo_avaliacao: string, tipo_avaliacao: string, peso: number,
    variantes: { letra_variante: string | null, questao_ids: string[] }[]
  }>()
);

export const iniciarGrupoExame = createAction(
  '[Lms] Iniciar Grupo Exame',
  props<{ grupo_id: string, alocacao_id: string }>()
);

export const reatribuirVariante = createAction(
  '[Lms] Reatribuir Variante',
  props<{ grupo_id: string, matricula_id: string, exame_id: string }>()
);

export const apagarGrupoExame = createAction('[Lms] Apagar Grupo Exame', props<{ grupo_id: string, alocacao_id: string }>());

export const carregarAtribuicoesGrupo = createAction('[Lms] Carregar Atribuicoes Grupo', props<{ grupo_id: string }>());
export const carregarAtribuicoesGrupoSucesso = createAction(
  '[Lms] Carregar Atribuicoes Grupo Sucesso',
  props<{ grupo_id: string, atribuicoes: LmsAtribuicaoVariante[] }>()
);

// Continuam por variante individual — publicar/despublicar sozinho já
// não chega para os alunos começarem (ver docstring de LMSExame no
// back-end), mas continua útil para esconder temporariamente UMA
// variante sem desfazer o INICIAR do grupo inteiro.
export const publicarExame = createAction('[Lms] Publicar Exame', props<{ exame_id: string, alocacao_id: string }>());
export const despublicarExame = createAction('[Lms] Despublicar Exame', props<{ exame_id: string, alocacao_id: string }>());

export const carregarExameDetalhe = createAction('[Lms] Carregar Exame Detalhe', props<{ exame_id: string }>());
export const carregarExameDetalheSucesso = createAction(
  '[Lms] Carregar Exame Detalhe Sucesso',
  props<{ exame: LmsExameDetalhe }>()
);
export const limparExameDetalhe = createAction('[Lms] Limpar Exame Detalhe');

export const carregarResultadosGrupo = createAction('[Lms] Carregar Resultados Grupo', props<{ grupo_id: string }>());
export const carregarResultadosGrupoSucesso = createAction(
  '[Lms] Carregar Resultados Grupo Sucesso',
  props<{ grupo_id: string, resultados: LmsResultadoAlunoExame[] }>()
);

// Corrige questões ABERTA pendentes e/ou sobrescreve o total (caso
// "prova presencial, o professor corrige sempre") — depois de
// sucesso, volta a carregar os resultados do grupo (grupo_id só serve
// para o refetch, não vai no corpo do pedido).
export const corrigirTentativa = createAction(
  '[Lms] Corrigir Tentativa',
  props<{
    exame_id: string, matricula_id: string, grupo_id: string,
    correcoes: LmsCorrecaoQuestaoInput[], nota_obtida_override: number | null
  }>()
);
