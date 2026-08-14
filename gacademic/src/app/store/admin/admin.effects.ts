import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AdminActions from './admin.actions';
import { TenantResumo } from './admin.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class AdminEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarTenants$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.carregarTenants),
      switchMap(() => this.http.get<TenantResumo[]>('/api/v1/admin/tenants').pipe(
        map(tenants => AdminActions.carregarTenantsSucesso({ tenants })),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as instituições.'
        })))
      ))
    )
  );

  atualizarStatusTenant$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.atualizarStatusTenant),
      switchMap(action => this.http.patch<{ mensagem: string }>(
        `/api/v1/admin/tenants/${action.tenant_id}/status`, { status: action.status }
      ).pipe(
        switchMap(resp => [
          AdminActions.carregarTenants(),
          AdminActions.adminOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o estado desta instituição.'
        })))
      ))
    )
  );
}
