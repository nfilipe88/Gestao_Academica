import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as EventosActions from './eventos.actions';
import { Evento } from './eventos.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class EventosEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarEventos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EventosActions.carregarEventos),
      switchMap(() => this.http.get<Evento[]>('/api/v1/eventos').pipe(
        map(eventos => EventosActions.carregarEventosSucesso({ eventos })),
        catchError(err => of(EventosActions.eventosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os eventos.'
        })))
      ))
    )
  );

  criarEvento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EventosActions.criarEvento),
      switchMap(action => this.http.post<Evento>('/api/v1/eventos', {
        titulo: action.titulo, data: action.data, descricao: action.descricao, publicado: action.publicado
      }).pipe(
        switchMap(() => [
          EventosActions.carregarEventos(),
          EventosActions.eventosOperacaoSucesso({ mensagem: 'Evento criado.' })
        ]),
        catchError(err => of(EventosActions.eventosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o evento.'
        })))
      ))
    )
  );

  atualizarEvento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EventosActions.atualizarEvento),
      switchMap(action => this.http.patch<Evento>(`/api/v1/eventos/${action.evento_id}`, {
        titulo: action.titulo, data: action.data, descricao: action.descricao, publicado: action.publicado
      }).pipe(
        switchMap(() => [
          EventosActions.carregarEventos(),
          EventosActions.eventosOperacaoSucesso({ mensagem: 'Evento atualizado.' })
        ]),
        catchError(err => of(EventosActions.eventosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o evento.'
        })))
      ))
    )
  );

  removerEvento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EventosActions.removerEvento),
      switchMap(action => this.http.delete(`/api/v1/eventos/${action.evento_id}`).pipe(
        switchMap(() => [
          EventosActions.carregarEventos(),
          EventosActions.eventosOperacaoSucesso({ mensagem: 'Evento removido.' })
        ]),
        catchError(err => of(EventosActions.eventosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível remover o evento.'
        })))
      ))
    )
  );

  adicionarFotoEvento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EventosActions.adicionarFotoEvento),
      switchMap(action => {
        const dados = new FormData();
        dados.append('ficheiro', action.ficheiro);
        return this.http.post<Evento>(`/api/v1/eventos/${action.evento_id}/fotos`, dados).pipe(
          switchMap(() => [EventosActions.carregarEventos()]),
          catchError(err => of(EventosActions.eventosOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar a foto.'
          })))
        );
      })
    )
  );

  removerFotoEvento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(EventosActions.removerFotoEvento),
      switchMap(action => this.http.delete<Evento>(`/api/v1/eventos/${action.evento_id}/fotos/${action.foto_id}`).pipe(
        switchMap(() => [EventosActions.carregarEventos()]),
        catchError(err => of(EventosActions.eventosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível remover a foto.'
        })))
      ))
    )
  );
}
