import { createAction, props } from '@ngrx/store';
import { Curso, Disciplina, GradeCurricular, ObjetivoAprendizagem, SerieAno, Turma } from './academic.models';

// Ações para Cursos
export const carregarCursos = createAction('[Academico] Carregar Cursos');
export const carregarCursosSucesso = createAction(
  '[Academico] Carregar Cursos Sucesso',
  props<{ cursos: Curso[] }>()
);
export const criarCurso = createAction(
  '[Academico] Criar Curso',
  props<{ nome: string }>()
);

// Ações para Séries/Anos (camada entre Curso e Turma, ex: "10º Ano" dentro
// de "Ensino Secundário")
export const carregarSeries = createAction('[Academico] Carregar Series');
export const carregarSeriesSucesso = createAction(
  '[Academico] Carregar Series Sucesso',
  props<{ series: SerieAno[] }>()
);
export const criarSerieAno = createAction(
  '[Academico] Criar Serie Ano',
  props<{ curso_id: string, nome: string }>()
);

// Ações para Turmas (Simplificado para o exemplo)
export const carregarTurmas = createAction('[Academico] Carregar Turmas');
export const carregarTurmasSucesso = createAction(
  '[Academico] Carregar Turmas Sucesso',
  props<{ turmas: Turma[] }>()
);
export const criarTurma = createAction(
  '[Academico] Criar Turma',
  props<{ serie_ano_id: string, nome_codigo: string, ano_letivo: number, vagas_maximas: number }>()
);

// Ações para Disciplinas (catálogo global da escola, não pertencem a
// nenhum Curso diretamente)
export const carregarDisciplinas = createAction('[Academico] Carregar Disciplinas');
export const carregarDisciplinasSucesso = createAction(
  '[Academico] Carregar Disciplinas Sucesso',
  props<{ disciplinas: Disciplina[] }>()
);
export const criarDisciplina = createAction(
  '[Academico] Criar Disciplina',
  props<{ nome: string, carga_horaria_total: number | null }>()
);

// Ações para Grade Curricular (associação Série/Ano <-> Disciplina)
export const carregarGradeCurricular = createAction('[Academico] Carregar Grade Curricular');
export const carregarGradeCurricularSucesso = createAction(
  '[Academico] Carregar Grade Curricular Sucesso',
  props<{ grade: GradeCurricular[] }>()
);
export const adicionarDisciplinaASerie = createAction(
  '[Academico] Adicionar Disciplina A Serie',
  props<{ serie_ano_id: string, disciplina_id: string }>()
);

// Ações para Objetivos de Aprendizagem (tópicos por disciplina, ex.:
// "Células" em Ciências) — ver store/academico/academic.models.ts.
export const carregarObjetivosAprendizagem = createAction(
  '[Academico] Carregar Objetivos Aprendizagem',
  props<{ disciplina_id?: string }>()
);
export const carregarObjetivosAprendizagemSucesso = createAction(
  '[Academico] Carregar Objetivos Aprendizagem Sucesso',
  props<{ objetivos: ObjetivoAprendizagem[] }>()
);
export const criarObjetivoAprendizagem = createAction(
  '[Academico] Criar Objetivo Aprendizagem',
  props<{ disciplina_id: string, nome: string, descricao: string | null }>()
);

// Ação genérica de falha: cobre qualquer um dos pedidos acima (carregar ou
// criar cursos/séries/turmas/disciplinas/grade/objetivos). Sem isto, um
// erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão (ver academic.effects.ts).
export const academicoOperacaoFalhou = createAction(
  '[Academico API] Operação Falhou',
  props<{ erro: string }>()
);
