import { createReducer, on } from '@ngrx/store';
import * as AcademicoActions from './academic.actions';
import { Curso, Disciplina, GradeCurricular, ObjetivoAprendizagem, SerieAno, Turma } from './academic.models';

export interface AcademicoState {
  cursos: Curso[];
  series: SerieAno[];
  turmas: Turma[];
  disciplinas: Disciplina[];
  gradeCurricular: GradeCurricular[];
  objetivosAprendizagem: ObjetivoAprendizagem[];
  erro: string | null;
}

export const initialState: AcademicoState = {
  cursos: [],
  series: [],
  turmas: [],
  disciplinas: [],
  gradeCurricular: [],
  objetivosAprendizagem: [],
  erro: null
};

export const academicoReducer = createReducer(
  initialState,
  on(AcademicoActions.carregarCursos, AcademicoActions.criarCurso, AcademicoActions.atualizarCurso, AcademicoActions.atualizarCursoSitePublico,
     AcademicoActions.carregarSeries, AcademicoActions.criarSerieAno,
     AcademicoActions.carregarTurmas, AcademicoActions.criarTurma,
     AcademicoActions.carregarDisciplinas, AcademicoActions.criarDisciplina,
     AcademicoActions.carregarGradeCurricular, AcademicoActions.adicionarDisciplinaASerie,
     AcademicoActions.carregarObjetivosAprendizagem, AcademicoActions.criarObjetivoAprendizagem,
    (state) => ({ ...state, erro: null })
  ),
  on(AcademicoActions.carregarCursosSucesso, (state, { cursos }) => ({ ...state, cursos })),
  on(AcademicoActions.carregarSeriesSucesso, (state, { series }) => ({ ...state, series })),
  on(AcademicoActions.carregarTurmasSucesso, (state, { turmas }) => ({ ...state, turmas })),
  on(AcademicoActions.carregarDisciplinasSucesso, (state, { disciplinas }) => ({ ...state, disciplinas })),
  on(AcademicoActions.carregarGradeCurricularSucesso, (state, { grade }) => ({ ...state, gradeCurricular: grade })),
  on(AcademicoActions.carregarObjetivosAprendizagemSucesso, (state, { objetivos }) => ({ ...state, objetivosAprendizagem: objetivos })),
  on(AcademicoActions.academicoOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
