import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as ComunicacoesActions from './comunicacoes.actions';
import { Comunicado } from './comunicacoes.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class ComunicacoesEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarComunicados$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ComunicacoesActions.carregarComunicados),
      switchMap(() => this.http.get<Comunicado[]>('/api/v1/comunicados').pipe(
        map(comunicados => ComunicacoesActions.carregarComunicadosSucesso({ comunicados })),
        catchError(err => of(ComunicacoesActions.comunicacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os comunicados.'
        })))
      ))
    )
  );

  criarComunicado$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ComunicacoesActions.criarComunicado),
      switchMap(action => this.http.post('/api/v1/comunicados', {
        tipo: action.tipo,
        titulo: action.titulo,
        corpo: action.corpo,
        destinatario_tipo: action.destinatario_tipo,
        destinatario_turma_id: action.destinatario_turma_id,
        destinatario_aluno_id: action.destinatario_aluno_id
      }).pipe(
        map(() => ComunicacoesActions.carregarComunicados()), // Atualiza a lista após criar
        catchError(err => of(ComunicacoesActions.comunicacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível enviar o comunicado.'
        })))
      ))
    )
  );
}
