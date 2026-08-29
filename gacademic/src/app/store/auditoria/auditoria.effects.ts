import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AuditoriaActions from './auditoria.actions';
import { AuditLogRegisto } from './auditoria.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

// Sem tenant_id -> escola do Gestor (token); com tenant_id -> qualquer
// escola, só o Super Admin tem acesso a essa rota no back-end.
function baseUrl(tenant_id?: string): string {
  return tenant_id ? `/api/v1/admin/tenants/${tenant_id}/auditoria` : '/api/v1/auditoria';
}

@Injectable()
export class AuditoriaEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarAuditoria$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuditoriaActions.carregarAuditoria),
      switchMap(action => {
        const filtros = action.filtros;
        const params: Record<string, string | number> = { page: action.page ?? 1, page_size: action.page_size ?? 25 };
        if (filtros?.entidade) params['entidade'] = filtros.entidade;
        if (filtros?.entidade_id) params['entidade_id'] = filtros.entidade_id;
        if (filtros?.acao) params['acao'] = filtros.acao;
        if (filtros?.autor_id) params['autor_id'] = filtros.autor_id;
        if (filtros?.data_inicio) params['data_inicio'] = filtros.data_inicio;
        if (filtros?.data_fim) params['data_fim'] = filtros.data_fim;
        return this.http.get<PaginaResultado<AuditLogRegisto>>(baseUrl(action.tenant_id), { params }).pipe(
          map(resp => AuditoriaActions.carregarAuditoriaSucesso({
            registos: resp.items,
            paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
          })),
          catchError(err => of(AuditoriaActions.auditoriaOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar a trilha de auditoria.'
          })))
        );
      })
    )
  );

  carregarEntidades$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuditoriaActions.carregarEntidades),
      switchMap(action => this.http.get<string[]>(`${baseUrl(action.tenant_id)}/entidades`).pipe(
        map(entidades => AuditoriaActions.carregarEntidadesSucesso({ entidades })),
        catchError(err => of(AuditoriaActions.auditoriaOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a lista de entidades.'
        })))
      ))
    )
  );
}
