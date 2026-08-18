import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as IndicadoresActions from './indicadores.actions';
import { AlunoRisco, Indicadores } from './indicadores.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class IndicadoresEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarIndicadores$ = createEffect(() =>
    this.actions$.pipe(
      ofType(IndicadoresActions.carregarIndicadores),
      switchMap(() => this.http.get<Indicadores>('/api/v1/indicadores').pipe(
        map(indicadores => IndicadoresActions.carregarIndicadoresSucesso({ indicadores })),
        catchError(err => of(IndicadoresActions.indicadoresOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os indicadores.'
        })))
      ))
    )
  );

  carregarRiscoEvasao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(IndicadoresActions.carregarRiscoEvasao),
      switchMap(() => this.http.get<AlunoRisco[]>('/api/v1/indicadores/risco-evasao').pipe(
        map(alunosEmRisco => IndicadoresActions.carregarRiscoEvasaoSucesso({ alunosEmRisco })),
        catchError(err => of(IndicadoresActions.indicadoresOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o risco de evasão.'
        })))
      ))
    )
  );
}
