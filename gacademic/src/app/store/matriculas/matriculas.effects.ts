import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as MatriculasActions from './matriculas.actions';
import { MatriculaDaTurma } from './matriculas.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class MatriculasEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarMatriculasDaTurma$ = createEffect(() =>
    this.actions$.pipe(
      ofType(MatriculasActions.carregarMatriculasDaTurma),
      switchMap(action => this.http.get<Omit<MatriculaDaTurma, 'turma_id'>[]>(
        `/api/v1/turmas/${action.turma_id}/matriculas`
      ).pipe(
        // O back-end não devolve turma_id em cada linha (é implícito no
        // URL); injetamo-lo aqui para o reducer conseguir filtrar por turma.
        map(matriculas => MatriculasActions.carregarMatriculasDaTurmaSucesso({
          turma_id: action.turma_id,
          matriculas: matriculas.map(m => ({ ...m, turma_id: action.turma_id }))
        })),
        catchError(err => of(MatriculasActions.matriculasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os alunos matriculados nesta turma.'
        })))
      ))
    )
  );

  criarMatricula$ = createEffect(() =>
    this.actions$.pipe(
      ofType(MatriculasActions.criarMatricula),
      switchMap(action => this.http.post('/api/v1/matriculas', {
        aluno_id: action.aluno_id,
        turma_id: action.turma_id,
        ano_letivo: action.ano_letivo
      }).pipe(
        // Atualiza só a lista desta turma após matricular
        map(() => MatriculasActions.carregarMatriculasDaTurma({ turma_id: action.turma_id })),
        catchError(err => of(MatriculasActions.matriculasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível matricular o aluno.'
        })))
      ))
    )
  );

  atualizarStatusMatricula$ = createEffect(() =>
    this.actions$.pipe(
      ofType(MatriculasActions.atualizarStatusMatricula),
      switchMap(action => this.http.patch(`/api/v1/matriculas/${action.matricula_id}/status`, {
        status_matricula: action.status_matricula, motivo: action.motivo ?? null
      }).pipe(
        map(() => MatriculasActions.carregarMatriculasDaTurma({ turma_id: action.turma_id })),
        catchError(err => of(MatriculasActions.matriculasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o estado da matrícula.'
        })))
      ))
    )
  );
}
