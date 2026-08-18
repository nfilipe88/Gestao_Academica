import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import { catchError, map, of, switchMap } from 'rxjs';
import * as PermissoesActions from './permissoes.actions';
import { PermissaoModulo } from './permissoes.models';

@Injectable()
export class PermissoesEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarPermissoes$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PermissoesActions.carregarPermissoes),
      switchMap(() => this.http.get<PermissaoModulo[]>('/api/v1/permissoes').pipe(
        map(permissoes => PermissoesActions.carregarPermissoesSucesso({ permissoes })),
        catchError(err => of(PermissoesActions.permissoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o mapa de permissões.'
        })))
      ))
    )
  );

  atualizarPermissao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PermissoesActions.atualizarPermissao),
      switchMap(action => this.http.patch<PermissaoModulo>(`/api/v1/permissoes/${action.id}`, action.operacoes).pipe(
        map(permissao => PermissoesActions.atualizarPermissaoSucesso({ permissao })),
        catchError(err => of(PermissoesActions.permissoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar esta célula do mapa.'
        })))
      ))
    )
  );
}
