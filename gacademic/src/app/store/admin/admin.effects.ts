import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AdminActions from './admin.actions';
import { AssinaturaTenant, PlanoSaaS, ResumoMrr, TenantResumo } from './admin.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class AdminEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarTenants$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.carregarTenants),
      switchMap(action => {
        const params: Record<string, string | number> = { page: action.page ?? 1, page_size: action.page_size ?? 25 };
        const filtros = action.filtros;
        if (filtros?.nome) params['nome'] = filtros.nome;
        if (filtros?.plano_id) params['plano_id'] = filtros.plano_id;
        if (filtros?.usuarios_min != null) params['usuarios_min'] = filtros.usuarios_min;
        if (filtros?.usuarios_max != null) params['usuarios_max'] = filtros.usuarios_max;
        return this.http.get<PaginaResultado<TenantResumo>>('/api/v1/admin/tenants', { params }).pipe(
          map(resp => AdminActions.carregarTenantsSucesso({
            tenants: resp.items,
            paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
          })),
          catchError(err => of(AdminActions.adminOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar as instituições.'
          })))
        );
      })
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

  // ==========================================
  // SAAS BILLING — Planos, Assinaturas e MRR
  // ==========================================

  carregarPlanos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.carregarPlanos),
      switchMap(() => this.http.get<PlanoSaaS[]>('/api/v1/admin/planos').pipe(
        map(planos => AdminActions.carregarPlanosSucesso({ planos })),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os planos.'
        })))
      ))
    )
  );

  criarPlano$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.criarPlano),
      switchMap(action => this.http.post<PlanoSaaS>('/api/v1/admin/planos', {
        nome: action.nome, preco_mensal: action.preco_mensal,
        limite_alunos: action.limite_alunos, descricao: action.descricao,
        dias_periodo_teste: action.dias_periodo_teste
      }).pipe(
        switchMap(plano => [
          AdminActions.carregarPlanos(),
          AdminActions.adminOperacaoSucesso({ mensagem: `Plano "${plano.nome}" criado.` })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o plano.'
        })))
      ))
    )
  );

  atualizarPlano$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.atualizarPlano),
      switchMap(action => this.http.patch<PlanoSaaS>(`/api/v1/admin/planos/${action.id}`, {
        nome: action.nome, preco_mensal: action.preco_mensal,
        limite_alunos: action.limite_alunos, descricao: action.descricao,
        dias_periodo_teste: action.dias_periodo_teste, ativo: action.ativo
      }).pipe(
        switchMap(plano => [
          AdminActions.carregarPlanos(),
          AdminActions.adminOperacaoSucesso({ mensagem: `Plano "${plano.nome}" atualizado.` })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o plano.'
        })))
      ))
    )
  );

  apagarPlano$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.apagarPlano),
      switchMap(action => this.http.delete<void>(`/api/v1/admin/planos/${action.id}`).pipe(
        switchMap(() => [
          AdminActions.carregarPlanos(),
          AdminActions.adminOperacaoSucesso({ mensagem: 'Plano apagado.' })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar o plano.'
        })))
      ))
    )
  );

  carregarMrr$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.carregarMrr),
      switchMap(() => this.http.get<ResumoMrr>('/api/v1/admin/mrr').pipe(
        map(mrr => AdminActions.carregarMrrSucesso({ mrr })),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o resumo de MRR.'
        })))
      ))
    )
  );

  carregarAssinaturaTenant$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.carregarAssinaturaTenant),
      switchMap(action => this.http.get<Partial<AssinaturaTenant>>(`/api/v1/admin/tenants/${action.tenant_id}/assinatura`).pipe(
        map(resp => AdminActions.carregarAssinaturaTenantSucesso({
          tenant_id: action.tenant_id,
          assinatura: resp && resp.id ? resp as AssinaturaTenant : null
        })),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a assinatura desta escola.'
        })))
      ))
    )
  );

  definirAssinaturaTenant$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.definirAssinaturaTenant),
      switchMap(action => this.http.put<AssinaturaTenant>(`/api/v1/admin/tenants/${action.tenant_id}/assinatura`, {
        plano_id: action.plano_id, proxima_cobranca: action.proxima_cobranca
      }).pipe(
        switchMap(assinatura => [
          AdminActions.carregarAssinaturaTenantSucesso({ tenant_id: action.tenant_id, assinatura }),
          AdminActions.carregarMrr(),
          AdminActions.adminOperacaoSucesso({ mensagem: 'Assinatura atualizada.' })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível definir a assinatura desta escola.'
        })))
      ))
    )
  );

  cancelarAssinaturaTenant$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AdminActions.cancelarAssinaturaTenant),
      switchMap(action => this.http.delete<void>(`/api/v1/admin/tenants/${action.tenant_id}/assinatura`).pipe(
        switchMap(() => [
          AdminActions.carregarAssinaturaTenant({ tenant_id: action.tenant_id }),
          AdminActions.carregarMrr(),
          AdminActions.adminOperacaoSucesso({ mensagem: 'Assinatura cancelada.' })
        ]),
        catchError(err => of(AdminActions.adminOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível cancelar a assinatura desta escola.'
        })))
      ))
    )
  );
}
