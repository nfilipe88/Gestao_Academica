import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient, HttpParams } from '@angular/common/http';
import * as DiarioActions from './diario.actions';
import { AlunoDiario, ConsolidadoTurmaDisciplina, PeriodoAvaliacao } from './diario.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class DiarioEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarAlunosDiario$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.carregarAlunosDiario),
      switchMap(action => this.http.get<AlunoDiario[]>(
        `/api/v1/diario/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}/alunos`
      ).pipe(
        map(alunos => DiarioActions.carregarAlunosDiarioSucesso({ alunos })),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os alunos desta turma/disciplina.'
        })))
      ))
    )
  );

  lancarFrequencias$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.lancarFrequencias),
      switchMap(action => this.http.post<{ total: number }>(
        `/api/v1/diario/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}/frequencias/lote`,
        {
          data_aula: action.data_aula,
          quantidade_aulas: action.quantidade_aulas,
          conteudo_programado: action.conteudo_programado,
          frequencias: action.frequencias
        }
      ).pipe(
        map(resp => DiarioActions.diarioOperacaoSucesso({
          mensagem: `Frequência registada para ${resp.total} aluno(s).`
        })),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível registar a frequência.'
        })))
      ))
    )
  );

  lancarNotas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.lancarNotas),
      switchMap(action => this.http.post<{ total: number }>(
        `/api/v1/diario/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}/notas/lote`,
        {
          periodo_avaliacao: action.periodo_avaliacao,
          tipo_avaliacao: action.tipo_avaliacao,
          data_avaliacao: action.data_avaliacao,
          notas: action.notas
        }
      ).pipe(
        map(resp => DiarioActions.diarioOperacaoSucesso({
          mensagem: `Notas registadas para ${resp.total} aluno(s).`
        })),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível registar as notas.'
        })))
      ))
    )
  );

  carregarConsolidado$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.carregarConsolidado),
      switchMap(action => {
        let params = new HttpParams();
        if (action.periodo_avaliacao) {
          params = params.set('periodo_avaliacao', action.periodo_avaliacao);
        }
        return this.http.get<ConsolidadoTurmaDisciplina>(
          `/api/v1/diario/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}/consolidado`,
          { params }
        ).pipe(
          map(consolidado => DiarioActions.carregarConsolidadoSucesso({ consolidado })),
          catchError(err => of(DiarioActions.diarioOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar o consolidado.'
          })))
        );
      })
    )
  );

  carregarPeriodos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.carregarPeriodos),
      switchMap(() => this.http.get<PeriodoAvaliacao[]>('/api/v1/diario/periodos').pipe(
        map(periodos => DiarioActions.carregarPeriodosSucesso({ periodos })),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os períodos de avaliação.'
        })))
      ))
    )
  );

  criarPeriodo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.criarPeriodo),
      switchMap(action => this.http.post('/api/v1/diario/periodos', { nome: action.nome }).pipe(
        switchMap(() => [
          DiarioActions.carregarPeriodos(),
          DiarioActions.diarioOperacaoSucesso({ mensagem: 'Período de avaliação criado.' })
        ]),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o período de avaliação.'
        })))
      ))
    )
  );

  trancarPeriodo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.trancarPeriodo),
      switchMap(action => this.http.patch<{ mensagem: string }>(`/api/v1/diario/periodos/${action.periodo_id}/trancar`, {}).pipe(
        switchMap(resp => [
          DiarioActions.carregarPeriodos(),
          DiarioActions.diarioOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível trancar o período de avaliação.'
        })))
      ))
    )
  );

  reabrirPeriodo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DiarioActions.reabrirPeriodo),
      switchMap(action => this.http.patch<{ mensagem: string }>(`/api/v1/diario/periodos/${action.periodo_id}/reabrir`, {}).pipe(
        switchMap(resp => [
          DiarioActions.carregarPeriodos(),
          DiarioActions.diarioOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(DiarioActions.diarioOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível reabrir o período de avaliação.'
        })))
      ))
    )
  );
}
