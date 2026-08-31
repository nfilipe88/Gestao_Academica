import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient, HttpParams } from '@angular/common/http';
import * as EstatisticasActions from './estatisticas.actions';
import { DashboardEstatisticas, RelatorioEstatisticas } from './estatisticas.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class EstatisticasEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarDashboard$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EstatisticasActions.carregarDashboardEstatisticas),
      switchMap(() => this.http.get<DashboardEstatisticas>('/api/v1/estatisticas/dashboard').pipe(
        map(dashboard => EstatisticasActions.carregarDashboardEstatisticasSucesso({ dashboard })),
        catchError(err => of(EstatisticasActions.estatisticasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o dashboard de estatísticas.'
        })))
      ))
    )
  );

  carregarRelatorio$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EstatisticasActions.carregarRelatorioEstatisticas),
      switchMap(({ data_inicio, data_fim }) => {
        const params = new HttpParams({ fromObject: { data_inicio, data_fim } });
        return this.http.get<RelatorioEstatisticas>('/api/v1/estatisticas/relatorio', { params }).pipe(
          map(relatorio => EstatisticasActions.carregarRelatorioEstatisticasSucesso({ relatorio })),
          catchError(err => of(EstatisticasActions.estatisticasOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar o relatório do período.'
          })))
        );
      })
    )
  );
}
