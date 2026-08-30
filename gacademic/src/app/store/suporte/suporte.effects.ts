import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as SuporteActions from './suporte.actions';
import { TicketComMensagens, TicketRegisto } from './suporte.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class SuporteEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarMeusTickets$ = createEffect(() =>
    this.actions$.pipe(
      ofType(SuporteActions.carregarMeusTickets),
      switchMap(action => this.http.get<PaginaResultado<TicketRegisto>>('/api/v1/suporte', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => SuporteActions.carregarMeusTicketsSucesso({
          tickets: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(SuporteActions.suporteOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os tickets.'
        })))
      ))
    )
  );

  criarTicket$ = createEffect(() =>
    this.actions$.pipe(
      ofType(SuporteActions.criarTicket),
      switchMap(action => this.http.post<{ mensagem: string; id: string }>('/api/v1/suporte', {
        nome: action.nome, email: action.email, assunto: action.assunto, mensagem: action.mensagem
      }).pipe(
        switchMap(resp => [
          SuporteActions.carregarMeusTickets({}),
          SuporteActions.suporteOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(SuporteActions.suporteOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível enviar o seu pedido.'
        })))
      ))
    )
  );

  carregarTicket$ = createEffect(() =>
    this.actions$.pipe(
      ofType(SuporteActions.carregarTicket),
      switchMap(action => this.http.get<TicketComMensagens>(`/api/v1/suporte/${action.id}`).pipe(
        map(ticket => SuporteActions.carregarTicketSucesso({ ticket })),
        catchError(err => of(SuporteActions.suporteOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar este ticket.'
        })))
      ))
    )
  );

  enviarMensagemTicket$ = createEffect(() =>
    this.actions$.pipe(
      ofType(SuporteActions.enviarMensagemTicket),
      switchMap(action => this.http.post<{ mensagem: string }>(`/api/v1/suporte/${action.id}/mensagens`, { corpo: action.corpo }).pipe(
        switchMap(() => [
          SuporteActions.carregarTicket({ id: action.id })
        ]),
        catchError(err => of(SuporteActions.suporteOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível enviar a mensagem.'
        })))
      ))
    )
  );
}
