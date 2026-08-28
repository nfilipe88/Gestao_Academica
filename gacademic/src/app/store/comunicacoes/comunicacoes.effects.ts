import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as ComunicacoesActions from './comunicacoes.actions';
import { Comunicado } from './comunicacoes.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class ComunicacoesEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarComunicados$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ComunicacoesActions.carregarComunicados),
      switchMap(action => this.http.get<PaginaResultado<Comunicado>>('/api/v1/comunicados', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => ComunicacoesActions.carregarComunicadosSucesso({
          comunicados: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(ComunicacoesActions.comunicacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os comunicados.'
        })))
      ))
    )
  );

  criarComunicado$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ComunicacoesActions.criarComunicado),
      switchMap(action => this.http.post<Comunicado>('/api/v1/comunicados', {
        tipo: action.tipo,
        titulo: action.titulo,
        corpo: action.corpo,
        destinatario_tipo: action.destinatario_tipo,
        destinatario_turma_id: action.destinatario_turma_id,
        destinatario_aluno_id: action.destinatario_aluno_id
      }).pipe(
        map(comunicado => ComunicacoesActions.criarComunicadoSucesso({ comunicado })),
        catchError(err => of(ComunicacoesActions.comunicacoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível enviar o comunicado.'
        })))
      ))
    )
  );

  // Efeito encadeado (ver criarComunicado$ acima): só depois de saber
  // que o comunicado ficou mesmo criado é que faz sentido voltar a
  // pedir a lista — assim o componente também tem uma ação própria
  // (criarComunicadoSucesso) a que se pode ligar para, por exemplo,
  // anexar um ficheiro ao comunicado que acabou de nascer.
  atualizarListaAposCriar$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ComunicacoesActions.criarComunicadoSucesso),
      map(() => ComunicacoesActions.carregarComunicados({}))
    )
  );
}
