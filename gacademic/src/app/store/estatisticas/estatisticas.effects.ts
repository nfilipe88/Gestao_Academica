import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient, HttpParams } from '@angular/common/http';
import * as EstatisticasActions from './estatisticas.actions';
import { DashboardEstatisticas, RelatorioEstatisticas } from './estatisticas.models';
import { catchError, map, of, switchMap } from 'rxjs';

// Sem tenant_id -> escola de quem está autenticado (token); com
// tenant_id -> qualquer escola, só o Super Admin tem acesso a essa
// rota no back-end (ver app/api/v1/admin.py).
function baseUrl(tenant_id?: string): string {
  return tenant_id ? `/api/v1/admin/tenants/${tenant_id}/estatisticas` : '/api/v1/estatisticas';
}

@Injectable()
export class EstatisticasEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarDashboard$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EstatisticasActions.carregarDashboardEstatisticas),
      switchMap(action => this.http.get<DashboardEstatisticas>(`${baseUrl(action.tenant_id)}/dashboard`).pipe(
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
      switchMap(({ data_inicio, data_fim, tenant_id }) => {
        const params = new HttpParams({ fromObject: { data_inicio, data_fim } });
        return this.http.get<RelatorioEstatisticas>(`${baseUrl(tenant_id)}/relatorio`, { params }).pipe(
          map(relatorio => EstatisticasActions.carregarRelatorioEstatisticasSucesso({ relatorio })),
          catchError(err => of(EstatisticasActions.estatisticasOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar o relatório do período.'
          })))
        );
      })
    )
  );
}
