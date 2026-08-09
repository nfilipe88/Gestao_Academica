import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AcademicoActions from './academic.actions';
import { Curso, Turma } from './academic.models';
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
        curso_id: action.curso_id,
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
}
