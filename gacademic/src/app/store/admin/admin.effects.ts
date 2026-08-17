import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AdminActions from './admin.actions';
import { TenantResumo } from './admin.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class AdminEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarTenants$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.carregarTenants),
      switchMap(action => this.http.get<PaginaResultado<TenantResumo>>('/api/v1/admin/tenants', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => AdminActions.carregarTenantsSucesso({
          tenants: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as instituições.'
        })))
      ))
    )
  );

  criarTenant$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.criarTenant),
      switchMap(action => this.http.post<{ mensagem: string }>('/api/v1/admin/tenants', {
        nome_fantasia: action.nome_fantasia, nif: action.nif, nome_gestor: action.nome_gestor,
        email_gestor: action.email_gestor, palavra_passe: action.palavra_passe
      }).pipe(
        switchMap(resp => [
          AdminActions.carregarTenants({}),
          AdminActions.adminOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar a escola.'
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
          AdminActions.carregarTenants({}),
          AdminActions.adminOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o estado desta instituição.'
        })))
      ))
    )
  );

  atualizarValidadeLicenca$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.atualizarValidadeLicenca),
      switchMap(action => this.http.patch<{ mensagem: string }>(
        `/api/v1/admin/tenants/${action.tenant_id}/validade-licenca`, { data_validade_licenca: action.data_validade_licenca }
      ).pipe(
        switchMap(resp => [
          AdminActions.carregarTenants({}),
          AdminActions.adminOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar a validade da licença.'
        })))
      ))
    )
  );

  processarValidadeLicencas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.processarValidadeLicencas),
      switchMap(() => this.http.post<{ mensagem: string, suspensos: number, alertados: number }>(
        '/api/v1/admin/validade-licenca/processar', {}
      ).pipe(
        switchMap(resp => [
          AdminActions.carregarTenants({}),
          AdminActions.adminOperacaoSucesso({
            mensagem: `${resp.mensagem} (${resp.suspensos} suspensa(s), ${resp.alertados} alertada(s)).`
          })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível processar a validade das licenças.'
        })))
      ))
    )
  );
}
