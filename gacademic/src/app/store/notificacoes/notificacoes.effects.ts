import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as NotificacoesActions from './notificacoes.actions';
import { Notificacao } from './notificacoes.models';
import { catchError, map, of, switchMap, timer } from 'rxjs';

const INTERVALO_POLLING_MS = 60_000;

@Injectable()
export class NotificacoesEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarNotificacoes$ = createEffect(() =>
    this.actions$.pipe(
      ofType(NotificacoesActions.carregarNotificacoes),
      switchMap(() => this.http.get<Notificacao[]>('/api/v1/notificacoes').pipe(
        map(notificacoes => NotificacoesActions.carregarNotificacoesSucesso({ notificacoes })),
        catchError(err => of(NotificacoesActions.notificacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as notificações.'
        })))
      ))
    )
  );

  // Disparado uma vez no arranque (dashboard-layout) e depois a cada
  // minuto, para o distintivo do sino refletir alertas criados por
  // outros utilizadores (comunicados, respostas a solicitações, etc.)
  // sem exigir um refrescar manual da página.
  carregarContagem$ = createEffect(() =>
    this.actions$.pipe(
      ofType(NotificacoesActions.carregarContagem),
      switchMap(() => timer(0, INTERVALO_POLLING_MS).pipe(
        switchMap(() => this.http.get<{ total_nao_lidas: number }>('/api/v1/notificacoes/contagem').pipe(
          map(resposta => NotificacoesActions.carregarContagemSucesso({ totalNaoLidas: resposta.total_nao_lidas })),
          catchError(err => of(NotificacoesActions.notificacoesOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar a contagem de notificações.'
          })))
        ))
      ))
    )
  );

  marcarComoLida$ = createEffect(() =>
    this.actions$.pipe(
      ofType(NotificacoesActions.marcarComoLida),
      switchMap(({ id }) => this.http.patch(`/api/v1/notificacoes/${id}/marcar-lida`, {}).pipe(
        map(() => NotificacoesActions.marcarComoLidaSucesso({ id })),
        catchError(err => of(NotificacoesActions.notificacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível marcar a notificação como lida.'
        })))
      ))
    )
  );

  marcarTodasComoLidas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(NotificacoesActions.marcarTodasComoLidas),
      switchMap(() => this.http.patch('/api/v1/notificacoes/marcar-todas-lidas', {}).pipe(
        map(() => NotificacoesActions.marcarTodasComoLidasSucesso()),
        catchError(err => of(NotificacoesActions.notificacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível marcar as notificações como lidas.'
        })))
      ))
    )
  );
}
