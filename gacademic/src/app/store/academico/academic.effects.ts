import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient, HttpParams } from '@angular/common/http';
import * as AcademicoActions from './academic.actions';
import { Curso, Disciplina, GradeCurricular, ObjetivoAprendizagem, SerieAno, Turma } from './academic.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class AcademicoEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  // --- CURSOS ---
  carregarCursos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarCursos),
      switchMap(() => this.http.get<Curso[]>('/api/v1/academico/cursos').pipe(
        map(cursos => AcademicoActions.carregarCursosSucesso({ cursos })),
        // Sem isto, um erro aqui mata o effect para o resto da sessão:
        // nenhuma ação carregarCursos voltaria a produzir efeito.
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os cursos.'
        })))
      ))
    )
  );

  criarCurso$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.criarCurso),
      switchMap(action => this.http.post('/api/v1/academico/cursos', { nome: action.nome }).pipe(
        map(() => AcademicoActions.carregarCursos()), // Atualiza a lista após criar
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o curso.'
        })))
      ))
    )
  );

  // --- SÉRIES/ANOS ---
  carregarSeries$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarSeries),
      switchMap(() => this.http.get<SerieAno[]>('/api/v1/academico/series').pipe(
        map(series => AcademicoActions.carregarSeriesSucesso({ series })),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as séries/anos.'
        })))
      ))
    )
  );

  criarSerieAno$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.criarSerieAno),
      switchMap(action => this.http.post('/api/v1/academico/series', {
        curso_id: action.curso_id,
        nome: action.nome
      }).pipe(
        map(() => AcademicoActions.carregarSeries()), // Atualiza a lista após criar
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar a série/ano.'
        })))
      ))
    )
  );

  // --- TURMAS ---
  carregarTurmas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarTurmas),
      switchMap(() => this.http.get<Turma[]>('/api/v1/academico/turmas').pipe(
        map(turmas => AcademicoActions.carregarTurmasSucesso({ turmas })),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as turmas.'
        })))
      ))
    )
  );

  criarTurma$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.criarTurma),
      switchMap(action => this.http.post('/api/v1/academico/turmas', {
        serie_ano_id: action.serie_ano_id,
        nome_codigo: action.nome_codigo,
        ano_letivo: action.ano_letivo,
        vagas_maximas: action.vagas_maximas
      }).pipe(
        map(() => AcademicoActions.carregarTurmas()), // Atualiza a lista após criar
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar a turma.'
        })))
      ))
    )
  );

  // --- DISCIPLINAS ---
  carregarDisciplinas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarDisciplinas),
      switchMap(() => this.http.get<Disciplina[]>('/api/v1/academico/disciplinas').pipe(
        map(disciplinas => AcademicoActions.carregarDisciplinasSucesso({ disciplinas })),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as disciplinas.'
        })))
      ))
    )
  );

  criarDisciplina$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.criarDisciplina),
      switchMap(action => this.http.post('/api/v1/academico/disciplinas', {
        nome: action.nome,
        carga_horaria_total: action.carga_horaria_total
      }).pipe(
        map(() => AcademicoActions.carregarDisciplinas()),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar a disciplina.'
        })))
      ))
    )
  );

  // --- GRADE CURRICULAR ---
  carregarGradeCurricular$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarGradeCurricular),
      switchMap(() => this.http.get<GradeCurricular[]>('/api/v1/academico/grade-curricular').pipe(
        map(grade => AcademicoActions.carregarGradeCurricularSucesso({ grade })),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a grade curricular.'
        })))
      ))
    )
  );

  adicionarDisciplinaASerie$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.adicionarDisciplinaASerie),
      switchMap(action => this.http.post('/api/v1/academico/grade-curricular', {
        serie_ano_id: action.serie_ano_id,
        disciplina_id: action.disciplina_id
      }).pipe(
        map(() => AcademicoActions.carregarGradeCurricular()),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível adicionar a disciplina à série.'
        })))
      ))
    )
  );

  // --- OBJETIVOS DE APRENDIZAGEM ---
  carregarObjetivosAprendizagem$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarObjetivosAprendizagem),
      switchMap(action => {
        let params = new HttpParams();
        if (action.disciplina_id) {
          params = params.set('disciplina_id', action.disciplina_id);
        }
        return this.http.get<ObjetivoAprendizagem[]>('/api/v1/academico/objetivos-aprendizagem', { params }).pipe(
          map(objetivos => AcademicoActions.carregarObjetivosAprendizagemSucesso({ objetivos })),
          catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar os objetivos de aprendizagem.'
          })))
        );
      })
    )
  );

  criarObjetivoAprendizagem$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.criarObjetivoAprendizagem),
      switchMap(action => this.http.post('/api/v1/academico/objetivos-aprendizagem', {
        disciplina_id: action.disciplina_id,
        nome: action.nome,
        descricao: action.descricao
      }).pipe(
        map(() => AcademicoActions.carregarObjetivosAprendizagem({})),
        catchError(err => of(AcademicoActions.academicoOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o objetivo de aprendizagem.'
        })))
      ))
    )
  );
}
