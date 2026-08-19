import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import { catchError, map, of, switchMap } from 'rxjs';
import * as PropinasActions from './propinas.actions';
import { LinhaPropina } from './propinas.models';

@Injectable()
export class PropinasEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarPropinas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PropinasActions.carregarPropinas),
      switchMap(action => this.http.get<LinhaPropina[]>('/api/v1/propinas', {
        params: { ano_letivo: action.ano_letivo }
      }).pipe(
        map(linhas => PropinasActions.carregarPropinasSucesso({ linhas })),
        catchError(err => of(PropinasActions.propinasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a tabela de propinas.'
        })))
      ))
    )
  );

  definirPropina$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PropinasActions.definirPropina),
      switchMap(action => this.http.put<LinhaPropina>(`/api/v1/propinas/serie/${action.serie_ano_id}`, {
        ano_letivo: action.ano_letivo, valor_mensalidade: action.valor_mensalidade, valor_matricula: action.valor_matricula
      }).pipe(
        map(linha => PropinasActions.definirPropinaSucesso({ linha })),
        catchError(err => of(PropinasActions.propinasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível guardar esta propina.'
        })))
      ))
    )
  );

  apagarPropina$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PropinasActions.apagarPropina),
      switchMap(action => this.http.delete<void>(`/api/v1/propinas/${action.propina_id}`).pipe(
        map(() => PropinasActions.apagarPropinaSucesso({ serie_ano_id: action.serie_ano_id })),
        catchError(err => of(PropinasActions.propinasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar esta propina.'
        })))
      ))
    )
  );
}
