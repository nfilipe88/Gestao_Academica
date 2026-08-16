import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as LmsActions from './lms.actions';
import { MaterialAula } from './lms.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class LmsEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarMateriais$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarMateriais),
      switchMap(action => this.http.get<MaterialAula[]>(
        `/api/v1/lms/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}/materiais`
      ).pipe(
        map(materiais => LmsActions.carregarMateriaisSucesso({ materiais })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os materiais de aula.'
        })))
      ))
    )
  );

  criarMaterial$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.criarMaterial),
      switchMap(action => this.http.post('/api/v1/lms/materiais', {
        turma_id: action.turma_id, disciplina_id: action.disciplina_id, titulo: action.titulo, corpo: action.corpo,
        objetivo_aprendizagem_id: action.objetivo_aprendizagem_id, publicado: action.publicado
      }).pipe(
        switchMap(() => [
          LmsActions.carregarMateriais({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: `Material "${action.titulo}" publicado.` })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível publicar o material.'
        })))
      ))
    )
  );

  atualizarMaterial$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.atualizarMaterial),
      switchMap(action => this.http.patch(`/api/v1/lms/materiais/${action.material_id}`, {
        titulo: action.titulo, corpo: action.corpo,
        objetivo_aprendizagem_id: action.objetivo_aprendizagem_id, publicado: action.publicado
      }).pipe(
        switchMap(() => [
          LmsActions.carregarMateriais({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: `Material "${action.titulo}" atualizado.` })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o material.'
        })))
      ))
    )
  );

  sugerirConteudo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.sugerirConteudo),
      switchMap(action => this.http.post<{ sugestao: string }>('/api/v1/lms/materiais/sugestao-conteudo', {
        turma_id: action.turma_id, disciplina_id: action.disciplina_id, titulo: action.titulo,
        objetivo_aprendizagem_id: action.objetivo_aprendizagem_id, instrucoes: action.instrucoes
      }).pipe(
        map(resp => LmsActions.sugerirConteudoSucesso({ sugestao: resp.sugestao })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível gerar uma sugestão de conteúdo.'
        })))
      ))
    )
  );

  apagarMaterial$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.apagarMaterial),
      switchMap(action => this.http.delete(`/api/v1/lms/materiais/${action.material_id}`).pipe(
        switchMap(() => [
          LmsActions.carregarMateriais({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Material apagado.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar o material.'
        })))
      ))
    )
  );
}
