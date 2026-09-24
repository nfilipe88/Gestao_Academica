import { inject, Injectable, PLATFORM_ID } from '@angular/core';
import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as NotificacoesActions from './notificacoes.actions';
import { Notificacao } from './notificacoes.models';
import { catchError, EMPTY, map, of, switchMap, takeUntil } from 'rxjs';
import { logout, sessaoExpirada } from '../auth/auth.actions';
import { pollingContagem, visibilidadeDoDocumento$ } from './polling-contagem';

const INTERVALO_POLLING_MS = 60_000;

@Injectable()
export class NotificacoesEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private documento = inject(DOCUMENT);

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

  // Disparado uma vez no arranque (dashboard-layout). Depois pergunta a cada
  // ~minuto (ver polling-contagem.ts): só com o separador visível, com
  // variação aleatória, com recuo se o servidor falhar, e pára no logout —
  // antes continuava a pedir sem sessão (401 atrás de 401).
  // Alternativa avaliada: SSE/WebSockets — ver RUNBOOK.md, secção "Notificações em tempo real".
  carregarContagem$ = createEffect(() =>
    this.actions$.pipe(
      ofType(NotificacoesActions.carregarContagem),
      switchMap(() => {
        if (!isPlatformBrowser(this.platformId)) return EMPTY;
        return pollingContagem(
          () => this.http.get<{ total_nao_lidas: number }>('/api/v1/notificacoes/contagem'),
          { base: INTERVALO_POLLING_MS, visivel$: visibilidadeDoDocumento$(this.documento) },
        ).pipe(
          takeUntil(this.actions$.pipe(ofType(logout, sessaoExpirada))),
          map(r => r.ok
            ? NotificacoesActions.carregarContagemSucesso({ totalNaoLidas: r.valor.total_nao_lidas })
            : NotificacoesActions.notificacoesOperacaoFalhou({
                erro: (r.erro as any)?.error?.detail || 'Não foi possível carregar a contagem de notificações.'
              })),
        );
      })
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
