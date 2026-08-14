import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as TarefasActions from './tarefas.actions';
import { Tarefa, TarefaComAvaliacoes } from './tarefas.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class TarefasEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarTarefas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TarefasActions.carregarTarefas),
      switchMap(action => this.http.get<Tarefa[]>(
        `/api/v1/tarefas/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}`
      ).pipe(
        map(tarefas => TarefasActions.carregarTarefasSucesso({ tarefas })),
        catchError(err => of(TarefasActions.tarefasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os trabalhos/tarefas.'
        })))
      ))
    )
  );

  criarTarefa$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TarefasActions.criarTarefa),
      switchMap(action => this.http.post('/api/v1/tarefas', {
        alocacao_id: action.alocacao_id,
        titulo: action.titulo,
        descricao: action.descricao,
        data_entrega: action.data_entrega,
        valor_maximo: action.valor_maximo,
        periodo_avaliacao: action.periodo_avaliacao
      }).pipe(
        switchMap(() => [
          TarefasActions.carregarTarefas({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          TarefasActions.tarefasOperacaoSucesso({ mensagem: 'Trabalho/tarefa criado(a) com sucesso.' })
        ]),
        catchError(err => of(TarefasActions.tarefasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o trabalho/tarefa.'
        })))
      ))
    )
  );

  carregarTarefaDetalhe$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TarefasActions.carregarTarefaDetalhe),
      switchMap(action => this.http.get<TarefaComAvaliacoes>(`/api/v1/tarefas/${action.tarefa_id}`).pipe(
        map(tarefa => TarefasActions.carregarTarefaDetalheSucesso({ tarefa })),
        catchError(err => of(TarefasActions.tarefasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o trabalho/tarefa.'
        })))
      ))
    )
  );

  avaliarTarefa$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TarefasActions.avaliarTarefa),
      switchMap(action => this.http.post<{ mensagem: string }>(
        `/api/v1/tarefas/${action.tarefa_id}/avaliar`, { avaliacoes: action.avaliacoes }
      ).pipe(
        switchMap(resp => [
          TarefasActions.carregarTarefaDetalhe({ tarefa_id: action.tarefa_id }),
          TarefasActions.tarefasOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(TarefasActions.tarefasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível guardar a avaliação.'
        })))
      ))
    )
  );
}
